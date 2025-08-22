'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Search,
  Filter,
  X,
  Plus,
  Settings,
  Save,
  FolderOpen,
  ChevronDown,
  Calendar,
  Hash,
  Tag,
  Star,
  Trash2
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Separator } from '@/components/ui/separator';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { formatDate, parseSearchQuery } from '@/lib/utils';
import type { FilterState, SortState } from '@/types/api';

interface SmartFilterBarProps {
  placeholder?: string;
  initialFilters?: Partial<FilterState>;
  onFiltersChange?: (filters: FilterState) => void;
  onSortChange?: (sort: SortState) => void;
  savedViews?: SavedView[];
  onSaveView?: (name: string, filters: FilterState) => void;
  onLoadView?: (view: SavedView) => void;
  onDeleteView?: (viewId: string) => void;
  suggestions?: string[];
  className?: string;
}

interface SavedView {
  id: string;
  name: string;
  filters: FilterState;
  isDefault?: boolean;
  createdAt: string;
}

interface FilterChip {
  type: 'search' | 'tag' | 'score' | 'date' | 'source' | 'status';
  label: string;
  value: string | number | [number, number] | [Date, Date];
  removable?: boolean;
}

export function SmartFilterBar({
  placeholder = 'Søk leads, bedrifter, e-poster...',
  initialFilters = {},
  onFiltersChange,
  onSortChange,
  savedViews = [],
  onSaveView,
  onLoadView,
  onDeleteView,
  suggestions = [],
  className = ''
}: SmartFilterBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [filters, setFilters] = useState<FilterState>({
    search: '',
    tags: [],
    scoreRange: [0, 100],
    sources: [],
    ...initialFilters
  });

  const [searchValue, setSearchValue] = useState(filters.search);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showSavedViews, setShowSavedViews] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveViewName, setSaveViewName] = useState('');

  const searchInputRef = useRef<HTMLInputElement>(null);
  const suggestionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);

  // Parse URL parameters on mount
  useEffect(() => {
    const urlFilters: Partial<FilterState> = {};

    const search = searchParams.get('q');
    if (search) urlFilters.search = search;

    const tags = searchParams.get('tags');
    if (tags) urlFilters.tags = tags.split(',');

    const scoreMin = searchParams.get('score_min');
    const scoreMax = searchParams.get('score_max');
    if (scoreMin || scoreMax) {
      urlFilters.scoreRange = [
        scoreMin ? parseInt(scoreMin) : 0,
        scoreMax ? parseInt(scoreMax) : 100
      ];
    }

    const sources = searchParams.get('sources');
    if (sources) urlFilters.sources = sources.split(',');

    const status = searchParams.get('status');
    if (status) urlFilters.status = status;

    if (Object.keys(urlFilters).length > 0) {
      const newFilters = { ...filters, ...urlFilters };
      setFilters(newFilters);
      setSearchValue(newFilters.search);
      onFiltersChange?.(newFilters);
    }
  }, [searchParams]);

  // Update URL when filters change
  const updateURL = (newFilters: FilterState) => {
    const params = new URLSearchParams();

    if (newFilters.search) params.set('q', newFilters.search);
    if (newFilters.tags.length > 0) params.set('tags', newFilters.tags.join(','));
    if (newFilters.scoreRange[0] > 0) params.set('score_min', newFilters.scoreRange[0].toString());
    if (newFilters.scoreRange[1] < 100) params.set('score_max', newFilters.scoreRange[1].toString());
    if (newFilters.sources.length > 0) params.set('sources', newFilters.sources.join(','));
    if (newFilters.status) params.set('status', newFilters.status);

    const url = params.toString() ? `?${params.toString()}` : '';
    router.push(url, { scroll: false });
  };

  const handleFiltersChange = (newFilters: FilterState) => {
    setFilters(newFilters);
    onFiltersChange?.(newFilters);
    updateURL(newFilters);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsedQuery = parseSearchQuery(searchValue);
    const newFilters = {
      ...filters,
      search: parsedQuery.search,
      tags: [...filters.tags, ...parsedQuery.tags]
    };
    handleFiltersChange(newFilters);
    setShowSuggestions(false);
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveSuggestionIndex(prev =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveSuggestionIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        if (activeSuggestionIndex >= 0) {
          e.preventDefault();
          setSearchValue(filteredSuggestions[activeSuggestionIndex]);
          setShowSuggestions(false);
          setActiveSuggestionIndex(-1);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setActiveSuggestionIndex(-1);
        break;
    }
  };

  const filteredSuggestions = suggestions.filter(suggestion =>
    suggestion.toLowerCase().includes(searchValue.toLowerCase()) &&
    suggestion !== searchValue
  ).slice(0, 8);

  const removeChip = (chipType: string, value?: string) => {
    let newFilters = { ...filters };

    switch (chipType) {
      case 'search':
        newFilters.search = '';
        setSearchValue('');
        break;
      case 'tag':
        newFilters.tags = filters.tags.filter(tag => tag !== value);
        break;
      case 'score':
        newFilters.scoreRange = [0, 100];
        break;
      case 'date':
        delete newFilters.dateRange;
        break;
      case 'source':
        newFilters.sources = filters.sources.filter(source => source !== value);
        break;
      case 'status':
        delete newFilters.status;
        break;
    }

    handleFiltersChange(newFilters);
  };

  const addTag = (tag: string) => {
    if (!filters.tags.includes(tag)) {
      handleFiltersChange({
        ...filters,
        tags: [...filters.tags, tag]
      });
    }
  };

  const clearAllFilters = () => {
    const emptyFilters: FilterState = {
      search: '',
      tags: [],
      scoreRange: [0, 100],
      sources: []
    };
    setSearchValue('');
    handleFiltersChange(emptyFilters);
  };

  const saveView = () => {
    if (saveViewName.trim() && onSaveView) {
      onSaveView(saveViewName.trim(), filters);
      setSaveViewName('');
      setShowSaveDialog(false);
    }
  };

  const getFilterChips = (): FilterChip[] => {
    const chips: FilterChip[] = [];

    if (filters.search) {
      chips.push({
        type: 'search',
        label: `Søk: "${filters.search}"`,
        value: filters.search
      });
    }

    filters.tags.forEach(tag => {
      chips.push({
        type: 'tag',
        label: `#${tag}`,
        value: tag
      });
    });

    if (filters.scoreRange[0] > 0 || filters.scoreRange[1] < 100) {
      chips.push({
        type: 'score',
        label: `Score: ${filters.scoreRange[0]}-${filters.scoreRange[1]}`,
        value: filters.scoreRange
      });
    }

    if (filters.dateRange) {
      chips.push({
        type: 'date',
        label: `Dato: ${formatDate(filters.dateRange[0], 'short')} - ${formatDate(filters.dateRange[1], 'short')}`,
        value: filters.dateRange
      });
    }

    filters.sources.forEach(source => {
      chips.push({
        type: 'source',
        label: `Kilde: ${source}`,
        value: source
      });
    });

    if (filters.status) {
      chips.push({
        type: 'status',
        label: `Status: ${filters.status}`,
        value: filters.status
      });
    }

    return chips;
  };

  const hasActiveFilters = getFilterChips().length > 0;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Main search bar */}
      <div className="flex items-center space-x-2">
        <div className="relative flex-1">
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              ref={searchInputRef}
              value={searchValue}
              onChange={(e) => {
                setSearchValue(e.target.value);
                setShowSuggestions(true);
                setActiveSuggestionIndex(-1);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              onKeyDown={handleSearchKeyDown}
              placeholder={placeholder}
              className="pl-10 pr-4"
            />
          </form>

          {/* Search suggestions */}
          {showSuggestions && filteredSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-md shadow-lg z-50 max-h-60 overflow-y-auto">
              {filteredSuggestions.map((suggestion, index) => (
                <div
                  key={suggestion}
                  ref={el => suggestionRefs.current[index] = el}
                  className={`px-4 py-2 cursor-pointer hover:bg-accent ${
                    index === activeSuggestionIndex ? 'bg-accent' : ''
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setSearchValue(suggestion);
                    setShowSuggestions(false);
                  }}
                >
                  <div className="flex items-center space-x-2">
                    <Search className="h-3 w-3 text-muted-foreground" />
                    <span>{suggestion}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Advanced filters button */}
        <Popover open={showAdvanced} onOpenChange={setShowAdvanced}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm">
              <Filter className="h-4 w-4 mr-2" />
              Filtre
              {hasActiveFilters && (
                <Badge variant="secondary" className="ml-2 h-5 w-5 p-0 flex items-center justify-center">
                  {getFilterChips().length}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80 p-0" align="end">
            <AdvancedFilters
              filters={filters}
              onFiltersChange={handleFiltersChange}
              onClose={() => setShowAdvanced(false)}
            />
          </PopoverContent>
        </Popover>

        {/* Saved views */}
        <Popover open={showSavedViews} onOpenChange={setShowSavedViews}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm">
              <FolderOpen className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-64 p-0" align="end">
            <SavedViews
              views={savedViews}
              onLoad={onLoadView}
              onDelete={onDeleteView}
              onClose={() => setShowSavedViews(false)}
            />
          </PopoverContent>
        </Popover>

        {/* Save current view */}
        {hasActiveFilters && onSaveView && (
          <Popover open={showSaveDialog} onOpenChange={setShowSaveDialog}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                <Save className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64" align="end">
              <div className="space-y-3">
                <div>
                  <Label htmlFor="view-name">Navn på visning</Label>
                  <Input
                    id="view-name"
                    value={saveViewName}
                    onChange={(e) => setSaveViewName(e.target.value)}
                    placeholder="Min visning"
                    onKeyDown={(e) => e.key === 'Enter' && saveView()}
                  />
                </div>
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" size="sm" onClick={() => setShowSaveDialog(false)}>
                    Avbryt
                  </Button>
                  <Button size="sm" onClick={saveView} disabled={!saveViewName.trim()}>
                    Lagre
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}

        {/* Clear all filters */}
        {hasActiveFilters && (
          <Button variant="outline" size="sm" onClick={clearAllFilters}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Filter chips */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-2">
          {getFilterChips().map((chip, index) => (
            <Badge
              key={`${chip.type}-${index}`}
              variant="secondary"
              className="flex items-center gap-1 pl-2 pr-1"
            >
              <ChipIcon type={chip.type} />
              <span className="text-xs">{chip.label}</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                onClick={() => removeChip(chip.type, typeof chip.value === 'string' ? chip.value : undefined)}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function ChipIcon({ type }: { type: string }) {
  switch (type) {
    case 'search':
      return <Search className="h-3 w-3" />;
    case 'tag':
      return <Tag className="h-3 w-3" />;
    case 'score':
      return <Star className="h-3 w-3" />;
    case 'date':
      return <Calendar className="h-3 w-3" />;
    case 'source':
      return <Hash className="h-3 w-3" />;
    case 'status':
      return <Settings className="h-3 w-3" />;
    default:
      return <Filter className="h-3 w-3" />;
  }
}

function AdvancedFilters({
  filters,
  onFiltersChange,
  onClose
}: {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onClose: () => void;
}) {
  const [localFilters, setLocalFilters] = useState(filters);

  const applyFilters = () => {
    onFiltersChange(localFilters);
    onClose();
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">Avanserte filtre</h4>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <Separator />

      {/* Score range */}
      <div className="space-y-2">
        <Label>Score område</Label>
        <div className="px-2">
          <Slider
            value={localFilters.scoreRange}
            onValueChange={(value) =>
              setLocalFilters({ ...localFilters, scoreRange: value as [number, number] })
            }
            min={0}
            max={100}
            step={1}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{localFilters.scoreRange[0]}</span>
            <span>{localFilters.scoreRange[1]}</span>
          </div>
        </div>
      </div>

      {/* Date range */}
      <div className="space-y-2">
        <Label>Dato periode</Label>
        <CalendarComponent
          mode="range"
          selected={{
            from: localFilters.dateRange?.[0],
            to: localFilters.dateRange?.[1]
          }}
          onSelect={(range) =>
            setLocalFilters({
              ...localFilters,
              dateRange: range?.from && range?.to ? [range.from, range.to] : undefined
            })
          }
          className="rounded-md border"
        />
      </div>

      {/* Sources */}
      <div className="space-y-2">
        <Label>Kilder</Label>
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {['LinkedIn', 'Hunter.io', 'Apollo', 'ZoomInfo', 'Clearbit'].map(source => (
            <div key={source} className="flex items-center space-x-2">
              <Checkbox
                id={source}
                checked={localFilters.sources.includes(source)}
                onCheckedChange={(checked) => {
                  if (checked) {
                    setLocalFilters({
                      ...localFilters,
                      sources: [...localFilters.sources, source]
                    });
                  } else {
                    setLocalFilters({
                      ...localFilters,
                      sources: localFilters.sources.filter(s => s !== source)
                    });
                  }
                }}
              />
              <Label htmlFor={source} className="text-sm">{source}</Label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      <div className="flex justify-end space-x-2">
        <Button variant="outline" size="sm" onClick={onClose}>
          Avbryt
        </Button>
        <Button size="sm" onClick={applyFilters}>
          Bruk filtre
        </Button>
      </div>
    </div>
  );
}

function SavedViews({
  views,
  onLoad,
  onDelete,
  onClose
}: {
  views: SavedView[];
  onLoad?: (view: SavedView) => void;
  onDelete?: (viewId: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">Lagrede visninger</h4>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <Separator />

      {views.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-4">
          Ingen lagrede visninger
        </p>
      ) : (
        <div className="space-y-2">
          {views.map(view => (
            <div key={view.id} className="flex items-center justify-between group">
              <Button
                variant="ghost"
                size="sm"
                className="flex-1 justify-start"
                onClick={() => {
                  onLoad?.(view);
                  onClose();
                }}
              >
                <Star className={`h-3 w-3 mr-2 ${view.isDefault ? 'text-yellow-500' : 'text-muted-foreground'}`} />
                <span className="truncate">{view.name}</span>
              </Button>
              {onDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                  onClick={() => onDelete(view.id)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}