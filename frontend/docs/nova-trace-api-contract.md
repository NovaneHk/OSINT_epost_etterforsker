# Nova Trace Future API Contract

Sprint 1 does not implement real backend calls. This contract exists so the frontend is shaped correctly from day one.

## Response wrappers

```ts
export type ApiSuccess<T> = {
  ok: true;
  data: T;
  meta?: Record<string, unknown>;
};

export type ApiError = {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

export type PaginatedResponse<T> = {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  hasNextPage: boolean;
};
```

## Endpoints

### Dashboard

```txt
GET /api/dashboard/metrics
GET /api/dashboard/trends?range=7d|30d|90d
GET /api/dashboard/activity
```

### Leads

```txt
GET /api/leads?page=1&pageSize=50&query=&scoreMin=&scoreMax=&sourceId=&status=
GET /api/leads/:id
PATCH /api/leads/:id
POST /api/leads/bulk
POST /api/leads/:id/copy-event
```

### Sources

```txt
GET /api/sources
GET /api/sources/health
GET /api/sources/:id
POST /api/sources
PATCH /api/sources/:id
POST /api/sources/:id/test
```

### Runs

```txt
GET /api/runs
GET /api/runs/active
GET /api/runs/:id
POST /api/runs
POST /api/runs/:id/cancel
GET /api/runs/:id/logs
```

### Exports/reports

```txt
POST /api/exports
GET /api/exports/:id
POST /api/reports
GET /api/reports/:id
```

## Error states

Every API-ready UI component should be able to represent:

- loading
- empty
- success
- partial success
- validation error
- permission error
- source unavailable
- rate limited
- unknown error

## Frontend rule

In Sprint 1, implement data functions that return mock data shaped like these future endpoints. Do not call real endpoints yet.
