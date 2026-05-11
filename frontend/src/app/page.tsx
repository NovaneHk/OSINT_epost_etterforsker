import { redirect } from 'next/navigation';

export default function RootPage() {
  redirect('/dashboard');
  // redirect() throws at runtime; this satisfies TypeScript's ReactNode return requirement
  return null;
}

