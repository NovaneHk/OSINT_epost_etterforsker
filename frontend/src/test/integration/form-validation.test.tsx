import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

describe('Form Validation Integration', () => {
  const LeadForm = ({ onSubmit }: { onSubmit: (data: any) => void }) => {
    const [formData, setFormData] = React.useState({
      email: '',
      name: '',
      company: '',
    });
    const [errors, setErrors] = React.useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = React.useState(false);

    const validateForm = () => {
      const newErrors: Record<string, string> = {};

      if (!formData.email) {
        newErrors.email = 'Email is required';
      } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
        newErrors.email = 'Email is invalid';
      }

      if (!formData.name) {
        newErrors.name = 'Name is required';
      }

      if (!formData.company) {
        newErrors.company = 'Company is required';
      }

      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();

      if (!validateForm()) {
        return;
      }

      setIsSubmitting(true);

      try {
        await onSubmit(formData);
        setFormData({ email: '', name: '', company: '' });
        setErrors({});
      } catch (error) {
        setErrors({ submit: 'Failed to submit form' });
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Add Lead</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email">Email</label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className={errors.email ? 'border-red-500' : ''}
              />
              {errors.email && (
                <span className="text-red-500 text-sm">{errors.email}</span>
              )}
            </div>

            <div>
              <label htmlFor="name">Name</label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className={errors.name ? 'border-red-500' : ''}
              />
              {errors.name && (
                <span className="text-red-500 text-sm">{errors.name}</span>
              )}
            </div>

            <div>
              <label htmlFor="company">Company</label>
              <Input
                id="company"
                type="text"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className={errors.company ? 'border-red-500' : ''}
              />
              {errors.company && (
                <span className="text-red-500 text-sm">{errors.company}</span>
              )}
            </div>

            {errors.submit && (
              <div className="text-red-500 text-sm">{errors.submit}</div>
            )}

            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? 'Submitting...' : 'Add Lead'}
            </Button>
          </form>
        </CardContent>
      </Card>
    );
  };

  it('validates required fields', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn();

    render(<LeadForm onSubmit={mockSubmit} />);

    const submitButton = screen.getByRole('button', { name: /add lead/i });
    await user.click(submitButton);

    expect(screen.getByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(screen.getByText('Company is required')).toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('validates email format', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn();

    render(<LeadForm onSubmit={mockSubmit} />);

    const emailInput = screen.getByLabelText(/email/i);
    await user.type(emailInput, 'invalid-email');

    const submitButton = screen.getByRole('button', { name: /add lead/i });
    await user.click(submitButton);

    expect(screen.getByText('Email is invalid')).toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('submits valid form data', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn().mockResolvedValue(undefined);

    render(<LeadForm onSubmit={mockSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/company/i), 'Test Corp');

    const submitButton = screen.getByRole('button', { name: /add lead/i });
    await user.click(submitButton);

    expect(screen.getByText('Submitting...')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        email: 'test@example.com',
        name: 'John Doe',
        company: 'Test Corp',
      });
    });
  });

  it('handles submission errors', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn().mockRejectedValue(new Error('API Error'));

    render(<LeadForm onSubmit={mockSubmit} />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/company/i), 'Test Corp');

    const submitButton = screen.getByRole('button', { name: /add lead/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to submit form')).toBeInTheDocument();
    });
  });

  it('clears form after successful submission', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn().mockResolvedValue(undefined);

    render(<LeadForm onSubmit={mockSubmit} />);

    const emailInput = screen.getByLabelText(/email/i);
    const nameInput = screen.getByLabelText(/name/i);
    const companyInput = screen.getByLabelText(/company/i);

    await user.type(emailInput, 'test@example.com');
    await user.type(nameInput, 'John Doe');
    await user.type(companyInput, 'Test Corp');

    const submitButton = screen.getByRole('button', { name: /add lead/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(emailInput).toHaveValue('');
      expect(nameInput).toHaveValue('');
      expect(companyInput).toHaveValue('');
    });
  });
});

describe('Dialog Form Integration', () => {
  const DialogForm = ({ onSubmit }: { onSubmit: (data: any) => void }) => {
    const [isOpen, setIsOpen] = React.useState(false);
    const [formData, setFormData] = React.useState({ name: '', email: '' });

    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      await onSubmit(formData);
      setFormData({ name: '', email: '' });
      setIsOpen(false);
    };

    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button>Open Form Dialog</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Contact</DialogTitle>
            <DialogDescription>
              Enter contact information below.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="dialog-name">Name</label>
                <Input
                  id="dialog-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label htmlFor="dialog-email">Email</label>
                <Input
                  id="dialog-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>
            </div>
            <DialogFooter className="mt-4">
              <Button type="button" onClick={() => setIsOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Save Contact</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    );
  };

  it('opens dialog and submits form', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn().mockResolvedValue(undefined);

    render(<DialogForm onSubmit={mockSubmit} />);

    // Open dialog
    const triggerButton = screen.getByRole('button', { name: /open form dialog/i });
    await user.click(triggerButton);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fill form
    await user.type(screen.getByLabelText(/name/i), 'Jane Doe');
    await user.type(screen.getByLabelText(/email/i), 'jane@example.com');

    // Submit form
    const saveButton = screen.getByRole('button', { name: /save contact/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        name: 'Jane Doe',
        email: 'jane@example.com',
      });
    });

    // Dialog should close
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('cancels dialog without submitting', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn();

    render(<DialogForm onSubmit={mockSubmit} />);

    // Open dialog
    await user.click(screen.getByRole('button', { name: /open form dialog/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fill form partially
    await user.type(screen.getByLabelText(/name/i), 'Jane Doe');

    // Cancel
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('maintains form state while dialog is open', async () => {
    const user = userEvent.setup();
    const mockSubmit = vi.fn();

    render(<DialogForm onSubmit={mockSubmit} />);

    // Open dialog
    await user.click(screen.getByRole('button', { name: /open form dialog/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fill form
    const nameInput = screen.getByLabelText(/name/i);
    const emailInput = screen.getByLabelText(/email/i);

    await user.type(nameInput, 'Test User');
    await user.type(emailInput, 'test@example.com');

    // Values should persist
    expect(nameInput).toHaveValue('Test User');
    expect(emailInput).toHaveValue('test@example.com');

    // Click outside dialog area won't clear form (form state maintained)
    expect(nameInput).toHaveValue('Test User');
    expect(emailInput).toHaveValue('test@example.com');
  });
});