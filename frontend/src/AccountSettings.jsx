import React, { useRef, useState } from 'react';
import { CheckCircle2, LoaderCircle, LockKeyhole, UserRound } from 'lucide-react';

export default function AccountSettings({ user, onPasswordChange }) {
  const [submitting, setSubmitting] = useState(false);
  const [showPasswords, setShowPasswords] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const feedback = useRef(null);
  const joined = user.date_joined
    ? new Intl.DateTimeFormat('pl-PL', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Warsaw' }).format(new Date(user.date_joined))
    : '—';

  async function submit(event) {
    event.preventDefault();
    if (submitting) return;
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setError(''); setSuccess('');
    if (data.new_password !== data.new_password_confirm) {
      setError('Nowe hasła muszą być takie same.');
      form.elements.new_password_confirm.focus();
      return;
    }
    setSubmitting(true);
    try {
      const result = await onPasswordChange(data);
      form.reset();
      setShowPasswords(false);
      setSuccess(result.detail);
    } catch (error) {
      setError(error.message);
    } finally {
      setSubmitting(false);
      // Move to the result so keyboard users hear the outcome as well.
      feedback.current?.focus();
    }
  }

  return <div className="settings-grid">
    <section className="settings-card" aria-labelledby="profile-title">
      <div className="settings-title"><UserRound size={21}/><h3 id="profile-title">Dane konta</h3></div>
      <p className="settings-intro">Twoje dane podane podczas rejestracji.</p>
      <dl className="profile-details">
        <div><dt>Imię</dt><dd>{user.name}</dd></div>
        <div><dt>Adres e-mail</dt><dd>{user.email}</dd></div>
        <div><dt>Data dołączenia</dt><dd>{joined}</dd></div>
      </dl>
    </section>
    <section className="settings-card" aria-labelledby="password-title">
      <div className="settings-title"><LockKeyhole size={21}/><h3 id="password-title">Zmiana hasła</h3></div>
      <p className="settings-intro">Ustaw nowe hasło, aby zadbać o swoje konto.</p>
      <form className="password-form" onSubmit={submit} aria-busy={submitting}>
        <label htmlFor="old-password">Obecne hasło<input id="old-password" name="old_password" type={showPasswords ? 'text' : 'password'} autoComplete="current-password" maxLength={128} required disabled={submitting}/></label>
        <label htmlFor="new-password">Nowe hasło<input id="new-password" name="new_password" type={showPasswords ? 'text' : 'password'} autoComplete="new-password" minLength={10} maxLength={128} aria-describedby="password-hint" required disabled={submitting}/></label>
        <label htmlFor="confirm-password">Powtórz nowe hasło<input id="confirm-password" name="new_password_confirm" type={showPasswords ? 'text' : 'password'} autoComplete="new-password" minLength={10} maxLength={128} required disabled={submitting}/></label>
        <p id="password-hint" className="password-hint">Co najmniej 10 znaków. Unikaj popularnych haseł, samych cyfr i danych podobnych do Twojego imienia lub e-maila.</p>
        <label className="password-visibility"><input type="checkbox" checked={showPasswords} onChange={event => setShowPasswords(event.target.checked)} disabled={submitting}/>Pokaż hasła</label>
        <div ref={feedback} tabIndex={-1} className="password-feedback">
          {error && <p className="form-error" role="alert">{error}</p>}
          {success && <p className="form-success" role="status"><CheckCircle2 size={18}/>{success}</p>}
        </div>
        <button className="button lime" type="submit" disabled={submitting}>{submitting ? <><LoaderCircle size={18} className="spin"/>Zapisywanie…</> : <><LockKeyhole size={17}/>Zmień hasło</>}</button>
        <p className="password-hint session-hint">Po zmianie hasła pozostaniesz zalogowany na tym urządzeniu. Pozostałe sesje konta stracą ważność.</p>
      </form>
    </section>
  </div>;
}

