export interface User {
    id: string;
    email: string;
    username: string;
    isAdmin: boolean;
}

export interface Contact {
    email: string;
    domain: string;
    name: string;
    role: string;
    company: string;
    status: ContactStatus;
    confidenceScore: number;
    overallScore: number;
    personaMatch: string;
    source: string;
    sourceUrl: string;
    extractedAt: string;
    validatedAt: string | null;
    sector: string;
}

export enum ContactStatus {
    UNVALIDATED = "unvalidated",
    VALIDATED = "validated",
    CONTACTED = "contacted",
    RESPONDED = "responded",
    BOUNCED = "bounced",
    INVALID = "invalid",
    BLOCKED = "blocked"
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface ApiError {
    status: number;
    message: string;
}