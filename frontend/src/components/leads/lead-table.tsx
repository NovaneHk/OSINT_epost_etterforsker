'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  ColumnDef,
  flexRender,
  Row,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  RowSelectionState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  ArrowUpDown,
  ChevronDown,
  Download,
  Mail,
  MoreHorizontal,
  Settings,
  Star,
  Tag,
  Trash2,
  Eye,
  Copy,
  ExternalLink
} from 'lucide-react';
import { formatDate, formatNumber, getInitials, getScoreColor } from '@/lib/utils';
import type { Lead, FilterState, SortState } from '@/types/api';

interface LeadTableProps {
  data: Lead[];
  loading?: boolean;
  totalCount?: number;
  filters?: FilterState;
  onFiltersChange?: (filters: FilterState) => void;
  onSortChange?: (sort: SortState) => void;
  onRowSelect?: (lead: Lead) => void;
  onBulkAction?: (action: string, leadIds: string[]) => void;
  onExport?: (leadIds?: string[]) => void;
  className?: string;
}

export function LeadTable({
  data,
  loading = false,
  totalCount = 0,
  filters,
  onFiltersChange,
  onSortChange,
  onRowSelect,
  onBulkAction,
  onExport,
  className = ''
}: LeadTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  // Define columns
  const columns = useMemo<ColumnDef<Lead>[]>(() => [
    {
      id: 'select',
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Velg alle"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Velg rad"
        />
      ),
      enableSorting: false,
      enableHiding: false,
      size: 40,
    },
    {
      accessorKey: 'name',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-8 px-2 lg:px-3"
        >
          Navn
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const lead = row.original;
        return (
          <div className="flex items-center space-x-3 min-w-0">
            <Avatar className="h-8 w-8 flex-shrink-0">
              <AvatarImage src={`https://avatar.vercel.sh/${lead.email}`} />
              <AvatarFallback className="text-xs">
                {getInitials(lead.name || lead.email || 'UK')}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <div className="font-medium truncate">{lead.name || 'Ukjent navn'}</div>
              <div className="text-sm text-muted-foreground truncate">
                {lead.email}
              </div>
            </div>
          </div>
        );
      },
      size: 250,
    },
    {
      accessorKey: 'company',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-8 px-2 lg:px-3"
        >
          Bedrift
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const lead = row.original;
        return (
          <div className="max-w-[200px]">
            <div className="font-medium truncate">{lead.company || '—'}</div>
            {lead.title && (
              <div className="text-sm text-muted-foreground truncate">
                {lead.title}
              </div>
            )}
          </div>
        );
      },
      size: 200,
    },
    {
      accessorKey: 'location',
      header: 'Lokasjon',
      cell: ({ row }) => (
        <div className="text-sm">
          {row.getValue('location') || '—'}
        </div>
      ),
      size: 120,
    },
    {
      accessorKey: 'tags',
      header: 'Tags',
      cell: ({ row }) => {
        const tags = row.getValue('tags') as string[];
        if (!tags || tags.length === 0) return <span className="text-muted-foreground">—</span>;

        return (
          <div className="flex flex-wrap gap-1 max-w-[150px]">
            {tags.slice(0, 2).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {tags.length > 2 && (
              <Badge variant="outline" className="text-xs">
                +{tags.length - 2}
              </Badge>
            )}
          </div>
        );
      },
      enableSorting: false,
      size: 150,
    },
    {
      accessorKey: 'score',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-8 px-2 lg:px-3"
        >
          Score
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const score = row.getValue('score') as number;
        if (!score) return <span className="text-muted-foreground">—</span>;

        return (
          <div className="flex items-center space-x-2">
            <div className={`font-medium ${getScoreColor(score)}`}>
              {score}
            </div>
            <div className="flex items-center">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star
                  key={i}
                  className={`h-3 w-3 ${
                    i < Math.floor(score / 20)
                      ? 'text-yellow-400 fill-current'
                      : 'text-gray-300'
                  }`}
                />
              ))}
            </div>
          </div>
        );
      },
      size: 120,
    },
    {
      accessorKey: 'sourceIds',
      header: 'Kilder',
      cell: ({ row }) => {
        const sources = row.getValue('sourceIds') as string[];
        if (!sources || sources.length === 0) return <span className="text-muted-foreground">—</span>;

        return (
          <div className="text-sm">
            {sources.length === 1 ? (
              <Badge variant="outline">{sources[0]}</Badge>
            ) : (
              <Badge variant="outline">{sources.length} kilder</Badge>
            )}
          </div>
        );
      },
      enableSorting: false,
      size: 100,
    },
    {
      accessorKey: 'createdAt',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-8 px-2 lg:px-3"
        >
          Opprettet
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {formatDate(row.getValue('createdAt'), 'short')}
        </div>
      ),
      size: 100,
    },
    {
      id: 'actions',
      header: 'Handlinger',
      cell: ({ row }) => {
        const lead = row.original;

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Åpne meny</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Handlinger</DropdownMenuLabel>
              <DropdownMenuSeparator />

              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                onClick={() => onRowSelect?.(lead)}
              >
                <Eye className="mr-2 h-4 w-4" />
                Vis detaljer
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                onClick={() => navigator.clipboard.writeText(lead.email || '')}
              >
                <Copy className="mr-2 h-4 w-4" />
                Kopier e-post
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                onClick={() => window.open(`mailto:${lead.email}`, '_blank')}
              >
                <Mail className="mr-2 h-4 w-4" />
                Send e-post
              </Button>

              {lead.company && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                  onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(lead.company)}`, '_blank')}
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Søk på bedrift
                </Button>
              )}

              <DropdownMenuSeparator />

              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-destructive"
                onClick={() => onBulkAction?.('delete', [lead.id])}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Slett
              </Button>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
      enableSorting: false,
      enableHiding: false,
      size: 80,
    },
  ], [onRowSelect, onBulkAction]);

  // Create table instance
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
    enableRowSelection: true,
    enableMultiRowSelection: true,
  });

  // Virtual scrolling setup
  const { rows } = table.getRowModel();
  const parentRef = React.useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
    overscan: 10,
  });

  // Handle sorting change
  const handleSortingChange = useCallback((newSorting: SortingState) => {
    setSorting(newSorting);
    if (onSortChange && newSorting.length > 0) {
      const sort = newSorting[0];
      onSortChange({
        field: sort.id,
        direction: sort.desc ? 'desc' : 'asc'
      });
    }
  }, [onSortChange]);

  // Get selected lead IDs
  const selectedLeadIds = useMemo(() => {
    return table.getSelectedRowModel().rows.map(row => row.original.id);
  }, [rowSelection]);

  // Bulk actions
  const handleBulkAction = (action: string) => {
    if (selectedLeadIds.length > 0) {
      onBulkAction?.(action, selectedLeadIds);
      setRowSelection({});
    }
  };

  if (loading && data.length === 0) {
    return <LeadTableSkeleton />;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Table controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {selectedLeadIds.length > 0 && (
            <>
              <Badge variant="secondary">
                {selectedLeadIds.length} valgt
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleBulkAction('addTags')}
              >
                <Tag className="mr-2 h-4 w-4" />
                Legg til tags
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onExport?.(selectedLeadIds)}
              >
                <Download className="mr-2 h-4 w-4" />
                Eksporter valgte
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleBulkAction('delete')}
                className="text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Slett valgte
              </Button>
            </>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <div className="text-sm text-muted-foreground">
            {formatNumber(totalCount)} leads totalt
          </div>

          {/* Column visibility */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="mr-2 h-4 w-4" />
                Kolonner
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Vis/skjul kolonner</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {table
                .getAllColumns()
                .filter(column => column.getCanHide())
                .map(column => (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    className="capitalize"
                    checked={column.getIsVisible()}
                    onCheckedChange={value => column.toggleVisibility(!!value)}
                  >
                    {column.id}
                  </DropdownMenuCheckboxItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onExport?.()}
          >
            <Download className="mr-2 h-4 w-4" />
            Eksporter alle
          </Button>
        </div>
      </div>

      {/* Virtual table */}
      <div className="border rounded-md">
        <div
          ref={parentRef}
          className="h-[600px] overflow-auto"
        >
          <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
            <Table>
              <TableHeader className="sticky top-0 bg-background z-10">
                {table.getHeaderGroups().map(headerGroup => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map(header => (
                      <TableHead
                        key={header.id}
                        style={{ width: header.getSize() }}
                        className="border-b"
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {virtualizer.getVirtualItems().map(virtualRow => {
                  const row = rows[virtualRow.index] as Row<Lead>;
                  return (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() && "selected"}
                      style={{
                        transform: `translateY(${virtualRow.start}px)`,
                        position: 'absolute',
                        width: '100%',
                        height: `${virtualRow.size}px`,
                      }}
                      className="hover:bg-muted/50 cursor-pointer"
                      onClick={() => onRowSelect?.(row.original)}
                    >
                      {row.getVisibleCells().map(cell => (
                        <TableCell
                          key={cell.id}
                          style={{ width: cell.column.getSize() }}
                          className="py-3"
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-background/80 flex items-center justify-center">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
            <span className="text-sm text-muted-foreground">Laster leads...</span>
          </div>
        </div>
      )}
    </div>
  );
}

function LeadTableSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="h-8 w-32 skeleton"></div>
        <div className="flex items-center space-x-2">
          <div className="h-8 w-24 skeleton"></div>
          <div className="h-8 w-24 skeleton"></div>
        </div>
      </div>

      <div className="border rounded-md">
        <div className="p-4">
          {/* Header skeleton */}
          <div className="grid grid-cols-8 gap-4 mb-4 pb-2 border-b">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-4 skeleton"></div>
            ))}
          </div>

          {/* Rows skeleton */}
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="grid grid-cols-8 gap-4 py-3 border-b border-border/50">
              {Array.from({ length: 8 }).map((_, j) => (
                <div key={j} className="h-4 skeleton"></div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
