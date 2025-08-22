import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/utils';
import {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';

describe('Card Components', () => {
  describe('Card', () => {
    it('renders with default styling', () => {
      render(<Card data-testid="card">Card content</Card>);

      const card = screen.getByTestId('card');
      expect(card).toBeInTheDocument();
      expect(card).toHaveClass('rounded-lg', 'border', 'bg-card');
    });

    it('applies custom className', () => {
      render(<Card className="custom-class">Card content</Card>);

      const card = screen.getByText('Card content');
      expect(card).toHaveClass('custom-class');
    });

    it('forwards ref correctly', () => {
      const ref = vi.fn();
      render(<Card ref={ref}>Card content</Card>);

      expect(ref).toHaveBeenCalled();
    });
  });

  describe('CardHeader', () => {
    it('renders with proper styling', () => {
      render(<CardHeader data-testid="header">Header content</CardHeader>);

      const header = screen.getByTestId('header');
      expect(header).toBeInTheDocument();
      expect(header).toHaveClass('flex', 'flex-col', 'space-y-1.5', 'p-6');
    });

    it('applies custom className', () => {
      render(<CardHeader className="custom-header">Header</CardHeader>);

      const header = screen.getByText('Header');
      expect(header).toHaveClass('custom-header');
    });
  });

  describe('CardTitle', () => {
    it('renders with proper styling', () => {
      render(<CardTitle>Card Title</CardTitle>);

      const title = screen.getByText('Card Title');
      expect(title).toBeInTheDocument();
      expect(title).toHaveClass('text-2xl', 'font-semibold');
    });

    it('renders with custom className', () => {
      render(<CardTitle className="custom-title">Custom Title</CardTitle>);

      const title = screen.getByText('Custom Title');
      expect(title).toBeInTheDocument();
      expect(title).toHaveClass('custom-title');
    });
  });

  describe('CardDescription', () => {
    it('renders with proper styling', () => {
      render(<CardDescription>Card description</CardDescription>);

      const description = screen.getByText('Card description');
      expect(description).toBeInTheDocument();
      expect(description).toHaveClass('text-sm', 'text-muted-foreground');
    });

    it('applies custom className', () => {
      render(<CardDescription className="custom-desc">Description</CardDescription>);

      const description = screen.getByText('Description');
      expect(description).toHaveClass('custom-desc');
    });
  });

  describe('CardContent', () => {
    it('renders with proper styling', () => {
      render(<CardContent data-testid="content">Content</CardContent>);

      const content = screen.getByTestId('content');
      expect(content).toBeInTheDocument();
      expect(content).toHaveClass('p-6', 'pt-0');
    });

    it('applies custom className', () => {
      render(<CardContent className="custom-content">Content</CardContent>);

      const content = screen.getByText('Content');
      expect(content).toHaveClass('custom-content');
    });
  });

  describe('CardFooter', () => {
    it('renders with proper styling', () => {
      render(<CardFooter data-testid="footer">Footer content</CardFooter>);

      const footer = screen.getByTestId('footer');
      expect(footer).toBeInTheDocument();
      expect(footer).toHaveClass('flex', 'items-center', 'p-6', 'pt-0');
    });

    it('applies custom className', () => {
      render(<CardFooter className="custom-footer">Footer</CardFooter>);

      const footer = screen.getByText('Footer');
      expect(footer).toHaveClass('custom-footer');
    });
  });

  describe('Card Composition', () => {
    it('renders complete card structure', () => {
      render(
        <Card data-testid="complete-card">
          <CardHeader>
            <CardTitle>Test Card</CardTitle>
            <CardDescription>This is a test card</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card main content goes here</p>
          </CardContent>
          <CardFooter>
            <button>Action</button>
          </CardFooter>
        </Card>
      );

      expect(screen.getByTestId('complete-card')).toBeInTheDocument();
      expect(screen.getByText('Test Card')).toBeInTheDocument();
      expect(screen.getByText('This is a test card')).toBeInTheDocument();
      expect(screen.getByText('Card main content goes here')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    });

    it('works with minimal structure', () => {
      render(
        <Card>
          <CardContent>
            Simple card content
          </CardContent>
        </Card>
      );

      expect(screen.getByText('Simple card content')).toBeInTheDocument();
    });

    it('maintains proper semantic structure', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Article Title</CardTitle>
            <CardDescription>Article description</CardDescription>
          </CardHeader>
          <CardContent>
            <article>Article content</article>
          </CardContent>
        </Card>
      );

      const title = screen.getByText('Article Title');
      expect(title).toBeInTheDocument();

      const article = screen.getByRole('article');
      expect(article).toBeInTheDocument();
    });

    it('handles empty states gracefully', () => {
      render(<Card />);
      expect(document.querySelector('.rounded-lg')).toBeInTheDocument();
    });

    it('supports complex content', () => {
      const ComplexCard = () => (
        <Card className="w-96">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>📊</span>
              Analytics Dashboard
            </CardTitle>
            <CardDescription>
              View your website analytics and performance metrics
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-muted-foreground">Page Views</span>
                <div className="text-2xl font-bold">12,345</div>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Visitors</span>
                <div className="text-2xl font-bold">8,901</div>
              </div>
            </div>
          </CardContent>
          <CardFooter className="justify-between">
            <button className="btn-secondary">View Details</button>
            <button className="btn-primary">Export Data</button>
          </CardFooter>
        </Card>
      );

      render(<ComplexCard />);

      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
      expect(screen.getByText('12,345')).toBeInTheDocument();
      expect(screen.getByText('8,901')).toBeInTheDocument();
      expect(screen.getByText('View Details')).toBeInTheDocument();
      expect(screen.getByText('Export Data')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('maintains accessibility when used as article', () => {
      render(
        <Card role="article" aria-labelledby="card-title">
          <CardHeader>
            <CardTitle id="card-title">Accessible Card</CardTitle>
          </CardHeader>
          <CardContent>
            Content with proper labeling
          </CardContent>
        </Card>
      );

      const article = screen.getByRole('article');
      expect(article).toHaveAttribute('aria-labelledby', 'card-title');
    });

    it('supports ARIA attributes', () => {
      render(
        <Card
          aria-describedby="card-desc"
          tabIndex={0}
        >
          <CardContent id="card-desc">
            Focusable card content
          </CardContent>
        </Card>
      );

      const card = screen.getByRole('generic');
      expect(card).toHaveAttribute('aria-describedby', 'card-desc');
      expect(card).toHaveAttribute('tabIndex', '0');
    });
  });
});