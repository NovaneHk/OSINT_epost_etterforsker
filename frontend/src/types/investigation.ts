import { Investigation } from '@/components/InvestigationList';

export interface CreateInvestigationRequest {
    email: string;
}

export interface InvestigationsResponse {
    data: Investigation[];
    total: number;
}

export interface InvestigationResponse {
    data: Investigation;
}