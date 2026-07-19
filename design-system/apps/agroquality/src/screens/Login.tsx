import { useState, type FormEvent } from 'react';
import { Button, Field, Input } from '@automatizaesto/ui';
import { useAuth } from '../lib/auth';
import { LoginSplit } from '@automatizaesto/ui';

export function Login() {
  const { signIn, ready } = useAuth();
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await signIn(email.trim(), pass);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'No se pudo iniciar sesión.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <LoginSplit
      brand={{ mark: 'λ', name: 'AgroQuality' }}
      title="Inicia sesión"
      subtitle="Accede al panel de auditoría de calidad."
      showcase={
        <div className="max-w-sm">
          <p className="font-display text-3xl leading-snug">Auditoría de calidad post-cosecha, sin papeles.</p>
          <p className="mt-4 opacity-90">Inspecciona, califica y reporta desde un solo lugar.</p>
        </div>
      }
    >
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        {!ready && (
          <div className="rounded-sm border border-warning bg-warning-bg px-3 py-2 text-sm text-warning">
            Servicio de acceso no disponible. Verifica que el backend esté corriendo.
          </div>
        )}
        <Field label="Correo">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@empresa.com" autoComplete="email" />
        </Field>
        <Field label="Contraseña" error={err ?? undefined}>
          <Input type="password" value={pass} onChange={(e) => setPass(e.target.value)} placeholder="••••••••" autoComplete="current-password" />
        </Field>
        <Button type="submit" block disabled={busy || !ready}>
          {busy ? 'Entrando…' : 'Entrar'}
        </Button>
      </form>
    </LoginSplit>
  );
}
