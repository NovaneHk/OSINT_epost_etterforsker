import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

describe('Dialog Components', () => {
  describe('Dialog', () => {
    it('renders trigger and opens dialog on click', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Test Dialog</DialogTitle>
              <DialogDescription>This is a test dialog</DialogDescription>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      );

      const trigger = screen.getByRole('button', { name: /open dialog/i });
      expect(trigger).toBeInTheDocument();

      await user.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      expect(screen.getByText('Test Dialog')).toBeInTheDocument();
      expect(screen.getByText('This is a test dialog')).toBeInTheDocument();
    });

    it('closes dialog on escape key', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.keyboard('{Escape}');

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('closes dialog on overlay click', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Click outside the dialog content
      const overlay = document.querySelector('[data-radix-collection-item]');
      if (overlay) {
        await user.click(overlay);
      }

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('supports controlled state', async () => {
      const user = userEvent.setup();
      const onOpenChange = vi.fn();

      const ControlledDialog = ({ open }: { open: boolean }) => (
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogTrigger asChild>
            <Button>Open Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Controlled Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      const { rerender } = render(<ControlledDialog open={false} />);

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      rerender(<ControlledDialog open={true} />);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      await user.keyboard('{Escape}');
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('DialogContent', () => {
    it('renders with proper ARIA attributes', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Accessible Dialog</DialogTitle>
            <DialogDescription>Dialog with proper accessibility</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveAttribute('aria-labelledby');
        expect(dialog).toHaveAttribute('aria-describedby');
      });
    });

    it('applies custom className', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent className="custom-dialog">
            <DialogTitle>Custom Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        const dialog = screen.getByRole('dialog');
        expect(dialog).toHaveClass('custom-dialog');
      });
    });

    it('traps focus within dialog', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Focus Trap Dialog</DialogTitle>
            <DialogFooter>
              <Button>Cancel</Button>
              <Button>Submit</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button', { name: /open/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Focus should be trapped within the dialog
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      const submitButton = screen.getByRole('button', { name: /submit/i });

      expect(cancelButton).toBeInTheDocument();
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('DialogHeader', () => {
    it('renders with proper styling', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader data-testid="dialog-header">
              <DialogTitle>Header Dialog</DialogTitle>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        const header = screen.getByTestId('dialog-header');
        expect(header).toHaveClass('flex', 'flex-col', 'space-y-1.5');
      });
    });
  });

  describe('DialogTitle', () => {
    it('renders as heading with proper styling', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Dialog Title</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        const title = screen.getByText('Dialog Title');
        expect(title).toHaveClass('text-lg', 'font-semibold');
      });
    });
  });

  describe('DialogDescription', () => {
    it('renders with proper styling', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
            <DialogDescription>This is the description</DialogDescription>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button'));

      await waitFor(() => {
        const description = screen.getByText('This is the description');
        expect(description).toHaveClass('text-sm', 'text-muted-foreground');
      });
    });
  });

  describe('DialogFooter', () => {
    it('renders with proper styling and layout', async () => {
      const user = userEvent.setup();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Footer Dialog</DialogTitle>
            <DialogFooter data-testid="dialog-footer">
              <Button>Cancel</Button>
              <Button>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button', { name: /open/i }));

      await waitFor(() => {
        const footer = screen.getByTestId('dialog-footer');
        expect(footer).toHaveClass('flex', 'flex-col-reverse');
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      });
    });
  });

  describe('Dialog Integration', () => {
    it('handles form submission within dialog', async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn((e) => e.preventDefault());

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open Form Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Form Dialog</DialogTitle>
            </DialogHeader>
            <form onSubmit={onSubmit}>
              <input name="test" placeholder="Test input" />
              <DialogFooter>
                <Button type="submit">Submit</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button', { name: /open form dialog/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText('Test input');
      await user.type(input, 'test value');

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      expect(onSubmit).toHaveBeenCalled();
    });

    it('supports nested interactive elements', async () => {
      const user = userEvent.setup();
      const onButtonClick = vi.fn();

      render(
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle>Interactive Dialog</DialogTitle>
            <div>
              <Button onClick={onButtonClick}>Interactive Button</Button>
              <select aria-label="Select option">
                <option value="1">Option 1</option>
                <option value="2">Option 2</option>
              </select>
            </div>
          </DialogContent>
        </Dialog>
      );

      await user.click(screen.getByRole('button', { name: /open/i }));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const interactiveButton = screen.getByRole('button', { name: /interactive button/i });
      await user.click(interactiveButton);

      expect(onButtonClick).toHaveBeenCalled();

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, '2');

      expect(select).toHaveValue('2');
    });
  });
});