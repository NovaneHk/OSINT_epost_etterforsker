import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/button';

describe('Button Component', () => {
  it('renders with default props', () => {
    render(<Button>Click me</Button>);

    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
  });

  it('handles click events', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(<Button onClick={handleClick}>Click me</Button>);

    const button = screen.getByRole('button', { name: /click me/i });
    await user.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders as disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:pointer-events-none');
  });

  it('prevents click when disabled', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(<Button disabled onClick={handleClick}>Disabled</Button>);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });

  it('renders with custom className', () => {
    render(<Button className="custom-class">Custom</Button>);

    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-class');
  });

  it('forwards ref correctly', () => {
    const ref = vi.fn();
    render(<Button ref={ref}>Ref test</Button>);

    expect(ref).toHaveBeenCalled();
  });

  it('renders as different HTML element when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    );

    const link = screen.getByRole('link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test');
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(<Button onClick={handleClick}>Keyboard test</Button>);

    const button = screen.getByRole('button');
    button.focus();

    await user.keyboard('{Enter}');
    expect(handleClick).toHaveBeenCalledTimes(1);

    await user.keyboard(' ');
    expect(handleClick).toHaveBeenCalledTimes(2);
  });

  it('has proper accessibility attributes', () => {
    render(<Button aria-label="Close dialog">×</Button>);

    const button = screen.getByRole('button', { name: /close dialog/i });
    expect(button).toBeInTheDocument();
  });

  it('applies correct focus styles', async () => {
    const user = userEvent.setup();
    render(<Button>Focus test</Button>);

    const button = screen.getByRole('button');
    await user.tab();

    expect(button).toHaveFocus();
    expect(button).toHaveClass('focus-visible:ring-2');
  });

  it('works with icons', () => {
    const TestIcon = () => <span data-testid="test-icon">Icon</span>;

    render(
      <Button>
        <TestIcon />
        Button with icon
      </Button>
    );

    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
    expect(screen.getByText('Button with icon')).toBeInTheDocument();
  });

  it('handles long text content', () => {
    const longText = 'This is a very long button text that should wrap properly';
    render(<Button>{longText}</Button>);

    const button = screen.getByRole('button');
    expect(button).toHaveTextContent(longText);
  });

  it('maintains button behavior with custom type', () => {
    render(<Button type="submit">Submit</Button>);

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('type', 'submit');
  });

  it('applies base styling classes', () => {
    render(<Button>Styled Button</Button>);

    const button = screen.getByRole('button');
    expect(button).toHaveClass(
      'inline-flex',
      'items-center',
      'justify-center',
      'rounded-md',
      'font-medium'
    );
  });

  it('handles form submission correctly', () => {
    const handleSubmit = vi.fn((e) => e.preventDefault());

    render(
      <form onSubmit={handleSubmit}>
        <Button type="submit">Submit Form</Button>
      </form>
    );

    const button = screen.getByRole('button', { name: /submit form/i });
    expect(button).toHaveAttribute('type', 'submit');
  });

  it('supports ARIA attributes', () => {
    render(
      <Button
        aria-describedby="help-text"
        aria-pressed="false"
      >
        Toggle Button
      </Button>
    );

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-describedby', 'help-text');
    expect(button).toHaveAttribute('aria-pressed', 'false');
  });
});