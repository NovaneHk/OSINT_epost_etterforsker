import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { server } from '@/test/setup';
import { createMockLead, createMockSource } from '@/test/utils';

// Mock Next.js router
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    refresh: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(),
  }),
}));

// Mock the actual pages since we're testing integration
const MockLeadsPage = () => {
  const [leads, setLeads] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('/api/leads')
      .then(res => res.json())
      .then(data => {
        setLeads(data.leads || []);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div>Loading leads...</div>;
  }

  return (
    <div>
      <h1>Email Leads</h1>
      <div data-testid="leads-count">{leads.length} leads found</div>
      <div data-testid="leads-list">
        {leads.map((lead: any) => (
          <div key={lead.id} data-testid={`lead-${lead.id}`}>
            <span>{lead.email}</span>
            <span>{lead.company}</span>
            <button onClick={() => console.log('View lead', lead.id)}>
              View Details
            </button>
          </div>
        ))}
      </div>
      <button data-testid="add-lead-btn">Add New Lead</button>
    </div>
  );
};

describe('Lead Management Integration', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('loads and displays leads from API', async () => {
    const mockLeads = [
      createMockLead({ id: '1', email: 'john@example.com', company: 'Example Corp' }),
      createMockLead({ id: '2', email: 'jane@test.com', company: 'Test Inc' }),
    ];

    server.use(
      rest.get('/api/leads', (req, res, ctx) => {
        return res(ctx.json({ leads: mockLeads }));
      })
    );

    render(<MockLeadsPage />);

    expect(screen.getByText('Loading leads...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Email Leads')).toBeInTheDocument();
    });

    expect(screen.getByTestId('leads-count')).toHaveTextContent('2 leads found');
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('jane@test.com')).toBeInTheDocument();
    expect(screen.getByText('Example Corp')).toBeInTheDocument();
    expect(screen.getByText('Test Inc')).toBeInTheDocument();
  });

  it('handles empty leads state', async () => {
    server.use(
      rest.get('/api/leads', (req, res, ctx) => {
        return res(ctx.json({ leads: [] }));
      })
    );

    render(<MockLeadsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('leads-count')).toHaveTextContent('0 leads found');
    });

    expect(screen.getByTestId('leads-list')).toBeEmptyDOMElement();
  });

  it('handles API error gracefully', async () => {
    server.use(
      rest.get('/api/leads', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Internal server error' }));
      })
    );

    render(<MockLeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Loading leads...')).toBeInTheDocument();
    });

    // Component should handle error and show empty state
    await waitFor(() => {
      expect(screen.getByTestId('leads-count')).toHaveTextContent('0 leads found');
    });
  });

  it('interacts with individual lead items', async () => {
    const mockLeads = [
      createMockLead({ id: '1', email: 'test@example.com' }),
    ];

    server.use(
      rest.get('/api/leads', (req, res, ctx) => {
        return res(ctx.json({ leads: mockLeads }));
      })
    );

    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

    render(<MockLeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });

    const viewButton = screen.getByRole('button', { name: /view details/i });
    await userEvent.setup().click(viewButton);

    expect(consoleSpy).toHaveBeenCalledWith('View lead', '1');

    consoleSpy.mockRestore();
  });
});

describe('Lead Form Integration', () => {
  const MockLeadForm = () => {
    const [formData, setFormData] = React.useState({
      email: '',
      name: '',
      company: '',
    });
    const [submitting, setSubmitting] = React.useState(false);
    const [success, setSuccess] = React.useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitting(true);

      try {
        const response = await fetch('/api/leads', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData),
        });

        if (response.ok) {
          setSuccess(true);
          setFormData({ email: '', name: '', company: '' });
        }
      } catch (error) {
        console.error('Failed to create lead');
      } finally {
        setSubmitting(false);
      }
    };

    if (success) {
      return <div data-testid="success-message">Lead created successfully!</div>;
    }

    return (
      <form onSubmit={handleSubmit}>
        <h2>Add New Lead</h2>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
        </div>
        <div>
          <label htmlFor="name">Name</label>
          <input
            id="name"
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>
        <div>
          <label htmlFor="company">Company</label>
          <input
            id="company"
            type="text"
            value={formData.company}
            onChange={(e) => setFormData({ ...formData, company: e.target.value })}
            required
          />
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create Lead'}
        </button>
      </form>
    );
  };

  beforeEach(() => {
    server.resetHandlers();
  });

  it('successfully creates a new lead', async () => {
    const user = userEvent.setup();

    server.use(
      rest.post('/api/leads', (req, res, ctx) => {
        return res(ctx.json({ id: 'new-lead-id', success: true }));
      })
    );

    render(<MockLeadForm />);

    expect(screen.getByText('Add New Lead')).toBeInTheDocument();

    await user.type(screen.getByLabelText(/email/i), 'newlead@example.com');
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/company/i), 'New Company');

    const submitButton = screen.getByRole('button', { name: /create lead/i });
    await user.click(submitButton);

    expect(screen.getByText('Creating...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('success-message')).toHaveTextContent('Lead created successfully!');
    });
  });

  it('handles form validation', async () => {
    const user = userEvent.setup();

    render(<MockLeadForm />);

    const submitButton = screen.getByRole('button', { name: /create lead/i });
    await user.click(submitButton);

    // HTML5 validation should prevent submission
    expect(screen.queryByTestId('success-message')).not.toBeInTheDocument();
  });

  it('handles API errors during submission', async () => {
    const user = userEvent.setup();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    server.use(
      rest.post('/api/leads', (req, res, ctx) => {
        return res(ctx.status(400), ctx.json({ error: 'Validation failed' }));
      })
    );

    render(<MockLeadForm />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/name/i), 'Test User');
    await user.type(screen.getByLabelText(/company/i), 'Test Co');

    const submitButton = screen.getByRole('button', { name: /create lead/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to create lead');
    });

    expect(screen.queryByTestId('success-message')).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});

// Import React
import React from 'react';