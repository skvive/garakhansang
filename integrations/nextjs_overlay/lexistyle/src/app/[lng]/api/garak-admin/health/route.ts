import { NextResponse } from 'next/server';
import { requireAdmin } from '@/lib/auth/admin';
export const dynamic = 'force-dynamic';
export async function GET() {
  const admin = await requireAdmin();
  if (!admin) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  const base = process.env.GARAK_ADMIN_URL;
  if (!base || !base.startsWith('https://')) {
    return NextResponse.json({ configured: false, connected: false, reason: 'Missing HTTPS admin service URL' });
  }
  try {
    const response = await fetch(new URL('/api/health',base), { cache: 'no-store', signal: AbortSignal.timeout(3000) });
    if (!response.ok) return NextResponse.json({ configured: true, connected: false }, { status: 503 });
    const health = await response.json();
    return NextResponse.json({ configured: true, connected: true, mode: health.mode, payments: health.payments, synced: false });
  } catch {
    return NextResponse.json({ configured: true, connected: false, synced: false }, { status: 503 });
  }
}
