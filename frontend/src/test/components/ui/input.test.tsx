import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Input } from '@/components/ui/input';

describe('Input Component', () => {
  it('renders with default props', () => {
    render(<Input />);

    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveClass('flex', 'h-10', 'w-full', 'rounded-md', 'border');
  });

  it('applies placeholder text', () => {
    render(<Input placeholder="Enter your name" />);

    const input = screen.getByPlaceholderText('Enter your name');
    expect(input).toBeInTheDocument();
  });

  it('handles value changes', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    render(<Input onChange={handleChange} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'test input');

    expect(handleChange).toHaveBeenCalled();
    expect(input).toHaveValue('test input');
  });

  it('renders as disabled when disabled prop is true', () => {
    render(<Input disabled />);

    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
    expect(input).toHaveClass('disabled:cursor-not-allowed');
  });

  it('prevents input when disabled', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    render(<Input disabled onChange={handleChange} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'should not work');

    expect(handleChange).not.toHaveBeenCalled();
    expect(input).toHaveValue('');
  });

  it('renders with custom className', () => {
    render(<Input className="custom-input" />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('custom-input');
  });

  it('forwards ref correctly', () => {
    const ref = vi.fn();
    render(<Input ref={ref} />);

    expect(ref).toHaveBeenCalled();
  });

  it('supports different input types', () => {
    const { rerender } = render(<Input type="email" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('type', 'email');

    rerender(<Input type="password" />);
    expect(screen.getByDisplayValue('')).toHaveAttribute('type', 'password');

    rerender(<Input type="number" />);
    expect(screen.getByRole('spinbutton')).toHaveAttribute('type', 'number');
  });

  it('handles focus and blur events', async () => {
    const user = userEvent.setup();
    const handleFocus = vi.fn();
    const handleBlur = vi.fn();

    render(<Input onFocus={handleFocus} onBlur={handleBlur} />);

    const input = screen.getByRole('textbox');

    await user.click(input);
    expect(handleFocus).toHaveBeenCalledTimes(1);

    await user.tab();
    expect(handleBlur).toHaveBeenCalledTimes(1);
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    render(<Input />);

    const input = screen.getByRole('textbox');

    await user.tab();
    expect(input).toHaveFocus();

    await user.keyboard('Hello World');
    expect(input).toHaveValue('Hello World');
  });

  it('handles copy and paste operations', async () => {
    const user = userEvent.setup();
    render(<Input defaultValue="copy this text" />);

    const input = screen.getByRole('textbox');

    // Select all text
    await user.click(input);
    await user.keyboard('{Control>}a{/Control}');

    // Copy text
    await user.keyboard('{Control>}c{/Control}');

    // Clear and paste
    await user.clear(input);
    await user.keyboard('{Control>}v{/Control}');

    expect(input).toHaveValue('copy this text');
  });

  it('supports controlled component pattern', async () => {
    const user = userEvent.setup();
    let value = '';
    const setValue = vi.fn((newValue) => {
      value = newValue;
    });

    const ControlledInput = () => (
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
    );

    const { rerender } = render(<ControlledInput />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('');

    await user.type(input, 'controlled');
    expect(setValue).toHaveBeenCalled();

    // Simulate re-render with new value
    value = 'controlled';
    rerender(<ControlledInput />);
    expect(input).toHaveValue('controlled');
  });

  it('handles form submission', () => {
    const handleSubmit = vi.fn((e) => e.preventDefault());

    render(
      <form onSubmit={handleSubmit}>
        <Input name="testInput" defaultValue="form value" />
        <button type="submit">Submit</button>
      </form>
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('name', 'testInput');
    expect(input).toHaveValue('form value');
  });

  it('supports ARIA attributes', () => {
    render(
      <Input
        aria-label="Username"
        aria-describedby="username-help"
        aria-required="true"
      />
    );

    const input = screen.getByRole('textbox', { name: 'Username' });
    expect(input).toHaveAttribute('aria-describedby', 'username-help');
    expect(input).toHaveAttribute('aria-required', 'true');
  });

  it('handles validation states with custom styling', () => {
    render(<Input className="border-red-500" aria-invalid="true" />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('border-red-500');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('supports autocomplete attributes', () => {
    render(<Input autoComplete="email" />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('autoComplete', 'email');
  });

  it('handles minimum and maximum length', () => {
    render(<Input minLength={3} maxLength={10} />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('minLength', '3');
    expect(input).toHaveAttribute('maxLength', '10');
  });

  it('supports pattern validation', () => {
    render(<Input pattern="[0-9]{3}-[0-9]{3}-[0-9]{4}" />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('pattern', '[0-9]{3}-[0-9]{3}-[0-9]{4}');
  });

  it('handles readonly state', () => {
    render(<Input readOnly defaultValue="readonly value" />);

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('readOnly');
    expect(input).toHaveValue('readonly value');
  });

  it('supports custom data attributes', () => {
    render(<Input data-testid="custom-input" data-track="input-event" />);

    const input = screen.getByTestId('custom-input');
    expect(input).toHaveAttribute('data-track', 'input-event');
  });

  it('maintains focus styles', async () => {
    const user = userEvent.setup();
    render(<Input />);

    const input = screen.getByRole('textbox');
    await user.click(input);

    expect(input).toHaveFocus();
    expect(input).toHaveClass('focus-visible:ring-2');
  });
});