"""
Advanced Workflow Orchestration Engine for Phase 2
Automated OSINT intelligence gathering workflows
"""

import asyncio
import logging
import json
import yaml
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import croniter
from concurrent.futures import ThreadPoolExecutor

from core.security import SecurityManager
from core.performance import PerformanceMonitor
from core.error_handling import OSINTError, handle_errors
from integrations.connector_manager import get_connector_manager, OSINTResult

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class StepStatus(Enum):
    """Individual step status"""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    name: str
    connector: str
    config: Dict[str, Any]
    depends_on: List[str] = None
    timeout: int = 300  # 5 minutes default
    retry_count: int = 3
    status: StepStatus = StepStatus.WAITING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[OSINTResult] = None
    error: Optional[str] = None

@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_results: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class WorkflowResult:
    """Summary result of a completed workflow execution."""
    workflow_id: str
    status: str
    total_results: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class ScheduledWorkflow:
    """Scheduled workflow definition"""
    workflow_id: str
    name: str
    schedule: str  # Cron expression
    config: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class WorkflowEngine:
    """Advanced workflow orchestration for OSINT operations"""

    def __init__(self, security_manager=None, performance_monitor=None):
        self.security_manager = security_manager or SecurityManager()
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.connector_manager = get_connector_manager()

        # Workflow storage
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.completed_workflows: Dict[str, WorkflowExecution] = {}
        self.scheduled_workflows: Dict[str, ScheduledWorkflow] = {}
        self.workflow_templates: Dict[str, Dict] = {}

        # Execution control
        self.max_concurrent_workflows = 10
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.scheduler_running = False

        # Load workflow templates
        self._load_workflow_templates()

        # Load scheduled workflows
        self._load_scheduled_workflows()

        logger.info("WorkflowEngine initialized")

    def _load_workflow_templates(self):
        """Load workflow templates from configuration files"""
        try:
            templates_dir = Path("configs/workflows")
            if templates_dir.exists():
                for template_file in templates_dir.glob("*.yml"):
                    try:
                        with open(template_file, 'r') as f:
                            template = yaml.safe_load(f)
                            template_name = template_file.stem
                            self.workflow_templates[template_name] = template
                            logger.info(f"Loaded workflow template: {template_name}")
                    except Exception as e:
                        logger.error(f"Error loading template {template_file}: {e}")
            else:
                # Create default templates
                self._create_default_templates()

        except Exception as e:
            logger.error(f"Error loading workflow templates: {e}")

    def _create_default_templates(self):
        """Create default workflow templates"""
        self.workflow_templates = {
            'daily_intelligence': {
                'name': 'Daily Intelligence Gathering',
                'description': 'Automated daily OSINT collection and analysis',
                'schedule': '0 9 * * *',
                'enabled': True,
                'steps': [
                    {
                        'name': 'harvest_emails',
                        'connector': 'theharvester',
                        'config': {
                            'sources': ['google', 'bing', 'linkedin'],
                            'limit': 100
                        }
                    },
                    {
                        'name': 'check_breaches',
                        'connector': 'hibp',
                        'depends_on': ['harvest_emails'],
                        'config': {
                            'check_all_emails': True
                        }
                    },
                    {
                        'name': 'score_contacts',
                        'connector': 'internal',
                        'module': 'enhanced_scorer',
                        'depends_on': ['harvest_emails', 'check_breaches']
                    }
                ]
            },
            'threat_analysis': {
                'name': 'Threat Intelligence Analysis',
                'description': 'Comprehensive threat analysis workflow',
                'steps': [
                    {
                        'name': 'domain_scan',
                        'connector': 'spiderfoot',
                        'config': {
                            'modules': ['sfp_dnsresolve', 'sfp_subdomains']
                        }
                    },
                    {
                        'name': 'threat_intel',
                        'connector': 'intelowl',
                        'depends_on': ['domain_scan'],
                        'config': {
                            'analyzers': ['threat_intelligence', 'malware_analysis']
                        }
                    }
                ]
            }
        }

    def _load_scheduled_workflows(self):
        """Load scheduled workflows from configuration"""
        try:
            config_path = Path("configs/scheduled_workflows.yml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    scheduled_config = yaml.safe_load(f)

                for workflow_name, config in scheduled_config.get('workflows', {}).items():
                    if config.get('enabled', True):
                        scheduled_workflow = ScheduledWorkflow(
                            workflow_id=str(uuid.uuid4()),
                            name=workflow_name,
                            schedule=config['schedule'],
                            config=config,
                            enabled=True
                        )

                        # Calculate next run time
                        cron = croniter.croniter(config['schedule'], datetime.now())
                        scheduled_workflow.next_run = cron.get_next(datetime)

                        self.scheduled_workflows[workflow_name] = scheduled_workflow
                        logger.info(f"Scheduled workflow: {workflow_name} - Next run: {scheduled_workflow.next_run}")

        except Exception as e:
            logger.error(f"Error loading scheduled workflows: {e}")

    @handle_errors
    async def create_workflow(self, template_name: str, query: str, **kwargs) -> str:
        """Create a new workflow from template"""
        if template_name not in self.workflow_templates:
            raise OSINTError(f"Workflow template '{template_name}' not found")

        template = self.workflow_templates[template_name]
        workflow_id = str(uuid.uuid4())

        # Security validation
        validation_result = self.security_manager.validate_input(query, "search_query")
        if not validation_result['is_valid']:
            raise OSINTError(f"Invalid query: {validation_result['threats_detected']}")

        # Create workflow steps
        steps = []
        for step_config in template['steps']:
            step = WorkflowStep(
                name=step_config['name'],
                connector=step_config['connector'],
                config={**step_config.get('config', {}), 'query': query, **kwargs},
                depends_on=step_config.get('depends_on', []),
                timeout=step_config.get('timeout', 300),
                retry_count=step_config.get('retry_count', 3),
                results=[]
            )
            steps.append(step)

        # Create workflow execution
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            name=template['name'],
            description=template['description'],
            steps=steps,
            metadata={'template': template_name, 'query': query, **kwargs}
        )

        self.active_workflows[workflow_id] = workflow

        logger.info(f"Created workflow {workflow_id} from template {template_name}")
        return workflow_id

    @handle_errors
    async def execute_workflow(self, workflow_id: str) -> WorkflowExecution:
        """Execute a workflow"""
        if workflow_id not in self.active_workflows:
            raise OSINTError(f"Workflow {workflow_id} not found")

        workflow = self.active_workflows[workflow_id]

        if workflow.status != WorkflowStatus.PENDING:
            raise OSINTError(f"Workflow {workflow_id} is not in pending status")

        # Check concurrent workflow limit
        running_workflows = sum(1 for w in self.active_workflows.values()
                               if w.status == WorkflowStatus.RUNNING)

        if running_workflows >= self.max_concurrent_workflows:
            raise OSINTError("Maximum concurrent workflows reached")

        # Start workflow execution
        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = datetime.now()

        # Performance monitoring
        timer_id = self.performance_monitor.start_timer(f"workflow_{workflow_id}")

        try:
            logger.info(f"Starting workflow execution: {workflow_id}")

            # Execute steps
            await self._execute_workflow_steps(workflow)

            # Mark as completed
            workflow.status = WorkflowStatus.COMPLETED
            workflow.end_time = datetime.now()

            # Calculate total results
            workflow.total_results = sum(len(step.results or []) for step in workflow.steps)

            # Record performance
            self.performance_monitor.stop_timer(timer_id, 'workflow')

            # Move to completed workflows
            self.completed_workflows[workflow_id] = workflow
            del self.active_workflows[workflow_id]

            logger.info(f"Workflow {workflow_id} completed successfully with {workflow.total_results} results")

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.end_time = datetime.now()
            workflow.error = str(e)

            logger.error(f"Workflow {workflow_id} failed: {e}")

            # Move to completed workflows (even if failed)
            self.completed_workflows[workflow_id] = workflow
            del self.active_workflows[workflow_id]

            raise OSINTError(f"Workflow execution failed: {str(e)}")

        return workflow

    async def _execute_workflow_steps(self, workflow: WorkflowExecution):
        """Execute workflow steps with dependency management"""
        completed_steps = set()

        while len(completed_steps) < len(workflow.steps):
            # Find steps that can be executed (dependencies met)
            ready_steps = []
            for step in workflow.steps:
                if (step.status == StepStatus.WAITING and
                    all(dep in completed_steps for dep in (step.depends_on or []))):
                    ready_steps.append(step)

            if not ready_steps:
                # Check if we're stuck (circular dependencies or all remaining steps failed)
                remaining_steps = [s for s in workflow.steps if s.name not in completed_steps]
                if all(s.status == StepStatus.FAILED for s in remaining_steps):
                    raise OSINTError("All remaining steps have failed")
                else:
                    raise OSINTError("Circular dependency detected or no steps ready to execute")

            # Execute ready steps in parallel
            tasks = []
            for step in ready_steps:
                task = asyncio.create_task(
                    self._execute_step(step, workflow),
                    name=f"step_{step.name}"
                )
                tasks.append((step, task))

            # Wait for all tasks to complete
            for step, task in tasks:
                try:
                    await task
                    if step.status == StepStatus.COMPLETED:
                        completed_steps.add(step.name)
                except Exception as e:
                    logger.error(f"Step {step.name} failed: {e}")
                    step.status = StepStatus.FAILED
                    step.error = str(e)

                    # Decide whether to continue or fail the workflow
                    if step.config.get('critical', True):
                        raise OSINTError(f"Critical step {step.name} failed: {e}")
                    else:
                        # Mark as completed (but failed) to continue workflow
                        completed_steps.add(step.name)

    async def _execute_step(self, step: WorkflowStep, workflow: WorkflowExecution):
        """Execute a single workflow step"""
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()

        try:
            logger.info(f"Executing step: {step.name} in workflow {workflow.workflow_id}")

            # Get query from workflow metadata or step config
            query = step.config.get('query') or workflow.metadata.get('query', '')

            if step.connector == 'internal':
                # Handle internal modules
                results = await self._execute_internal_module(step, workflow)
            else:
                # Execute using connector
                results = await self.connector_manager.search(
                    step.connector,
                    query,
                    **{k: v for k, v in step.config.items() if k != 'query'}
                )

            step.results = results or []
            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()

            logger.info(f"Step {step.name} completed with {len(step.results)} results")

        except Exception as e:
            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            step.error = str(e)

            logger.error(f"Step {step.name} failed: {e}")
            raise

    async def _execute_internal_module(self, step: WorkflowStep, workflow: WorkflowExecution) -> List[OSINTResult]:
        """Execute internal processing modules"""
        module_name = step.config.get('module', '')

        if module_name == 'enhanced_scorer':
            # Collect all email results from previous steps
            all_emails = []
            for prev_step in workflow.steps:
                if prev_step.results:
                    for result in prev_step.results:
                        if result.data_type == 'email':
                            all_emails.append(result)

            # Score the emails (placeholder implementation)
            scored_results = []
            for email_result in all_emails:
                # Enhanced scoring logic would go here
                enhanced_result = OSINTResult(
                    source='enhanced_scorer',
                    data_type='scored_email',
                    content={
                        **email_result.content,
                        'enhanced_score': email_result.confidence * 1.2,  # Simple enhancement
                        'risk_factors': ['domain_age', 'breach_history']
                    },
                    confidence=min(email_result.confidence * 1.2, 1.0),
                    timestamp=datetime.now(),
                    metadata={'original_source': email_result.source}
                )
                scored_results.append(enhanced_result)

            return scored_results

        elif module_name == 'intelligence_reporter':
            # Generate intelligence report
            report_result = OSINTResult(
                source='intelligence_reporter',
                data_type='intelligence_report',
                content={
                    'report_id': str(uuid.uuid4()),
                    'workflow_id': workflow.workflow_id,
                    'total_findings': sum(len(s.results or []) for s in workflow.steps),
                    'generated_at': datetime.now().isoformat(),
                    'summary': 'Comprehensive OSINT intelligence report'
                },
                confidence=1.0,
                timestamp=datetime.now(),
                metadata={'workflow_name': workflow.name}
            )
            return [report_result]

        else:
            logger.warning(f"Unknown internal module: {module_name}")
            return []

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        # Check active workflows
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
        elif workflow_id in self.completed_workflows:
            workflow = self.completed_workflows[workflow_id]
        else:
            return {'error': f'Workflow {workflow_id} not found'}

        return {
            'workflow_id': workflow.workflow_id,
            'name': workflow.name,
            'description': workflow.description,
            'status': workflow.status.value,
            'start_time': workflow.start_time.isoformat() if workflow.start_time else None,
            'end_time': workflow.end_time.isoformat() if workflow.end_time else None,
            'total_results': workflow.total_results,
            'error': workflow.error,
            'steps': [
                {
                    'name': step.name,
                    'connector': step.connector,
                    'status': step.status.value,
                    'start_time': step.start_time.isoformat() if step.start_time else None,
                    'end_time': step.end_time.isoformat() if step.end_time else None,
                    'results_count': len(step.results or []),
                    'error': step.error
                }
                for step in workflow.steps
            ],
            'metadata': workflow.metadata
        }

    def get_workflow_results(self, workflow_id: str) -> List[OSINTResult]:
        """Get all results from a workflow"""
        workflow = None
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
        elif workflow_id in self.completed_workflows:
            workflow = self.completed_workflows[workflow_id]

        if not workflow:
            return []

        all_results = []
        for step in workflow.steps:
            if step.results:
                all_results.extend(step.results)

        return all_results

    def list_workflows(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workflows with optional status filter"""
        workflows = []

        # Add active workflows
        for workflow in self.active_workflows.values():
            if not status or workflow.status.value == status:
                workflows.append({
                    'workflow_id': workflow.workflow_id,
                    'name': workflow.name,
                    'status': workflow.status.value,
                    'start_time': workflow.start_time.isoformat() if workflow.start_time else None,
                    'total_results': workflow.total_results
                })

        # Add completed workflows
        for workflow in self.completed_workflows.values():
            if not status or workflow.status.value == status:
                workflows.append({
                    'workflow_id': workflow.workflow_id,
                    'name': workflow.name,
                    'status': workflow.status.value,
                    'start_time': workflow.start_time.isoformat() if workflow.start_time else None,
                    'end_time': workflow.end_time.isoformat() if workflow.end_time else None,
                    'total_results': workflow.total_results
                })

        # Sort by start time (newest first)
        workflows.sort(key=lambda x: x.get('start_time', ''), reverse=True)

        return workflows

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available workflow templates"""
        templates = []
        for name, template in self.workflow_templates.items():
            templates.append({
                'name': name,
                'display_name': template.get('name', name),
                'description': template.get('description', ''),
                'steps_count': len(template.get('steps', [])),
                'schedule': template.get('schedule'),
                'enabled': template.get('enabled', True)
            })

        return templates

    async def start_scheduler(self):
        """Start the workflow scheduler for automated execution"""
        if self.scheduler_running:
            logger.warning("Scheduler is already running")
            return

        self.scheduler_running = True
        logger.info("Starting workflow scheduler")

        while self.scheduler_running:
            try:
                await self._check_scheduled_workflows()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    async def _check_scheduled_workflows(self):
        """Check and execute scheduled workflows"""
        current_time = datetime.now()

        for workflow_name, scheduled_workflow in self.scheduled_workflows.items():
            if (scheduled_workflow.enabled and
                scheduled_workflow.next_run and
                current_time >= scheduled_workflow.next_run):

                try:
                    # Create and execute workflow
                    template_name = workflow_name
                    query = scheduled_workflow.config.get('default_query', 'scheduled_query')

                    workflow_id = await self.create_workflow(template_name, query)
                    await self.execute_workflow(workflow_id)

                    # Update last run time
                    scheduled_workflow.last_run = current_time

                    # Calculate next run time
                    cron = croniter.croniter(scheduled_workflow.schedule, current_time)
                    scheduled_workflow.next_run = cron.get_next(datetime)

                    logger.info(f"Executed scheduled workflow: {workflow_name}")

                except Exception as e:
                    logger.error(f"Failed to execute scheduled workflow {workflow_name}: {e}")

    def stop_scheduler(self):
        """Stop the workflow scheduler"""
        self.scheduler_running = False
        logger.info("Workflow scheduler stopped")

    def cleanup(self):
        """Cleanup workflow engine resources"""
        self.stop_scheduler()
        self.executor.shutdown(wait=True)
        logger.info("WorkflowEngine cleanup completed")


# Global workflow engine instance
_workflow_engine = None

def get_workflow_engine() -> WorkflowEngine:
    """Get global workflow engine instance"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
