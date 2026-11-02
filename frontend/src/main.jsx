import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, ArrowRight, Check, MapPin, Clock3, CalendarDays, UserRound, X, Menu, Dumbbell, MoveUpRight, LogOut, LoaderCircle, AlertCircle, CheckCircle2 } from 'lucide-react';
import './style.css';
import AccountSettings from './AccountSettings';

const money = value => new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 }).format(value);
const dayKey = value => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Warsaw' }).format(new Date(value));
const date = (value, options = {}) => new Intl.DateTimeFormat('pl-PL', { timeZone: 'Europe/Warsaw', day: 'numeric', month: 'long', ...options }).format(new Date(value));
const hour = value => new Intl.DateTimeFormat('pl-PL', { timeZone: 'Europe/Warsaw', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
const csrfToken = () => document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || '';

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`/api/${path}`, { method, credentials: 'same-origin', headers: {
    'Content-Type': 'application/json', ...(method !== 'GET' ? { 'X-CSRFToken': csrfToken() } : {}),
  }, ...(body ? { body: JSON.stringify(body) } : {}) });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.detail || (data ? Object.values(data).flat().join(' ') : 'Nie udało się połączyć. Spróbuj ponownie.'));
  return data;
}

function App() {
  const [catalog, setCatalog] = useState(null);
  const [account, setAccount] = useState({ user: null });
  const [loadError, setLoadError] = useState('');
  const [auth, setAuth] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState('');
  const [day, setDay] = useState('');
  const [location, setLocation] = useState('all');
  const [category, setCategory] = useState('all');
  const [mobile, setMobile] = useState(false);
  const [pending, setPending] = useState(null);
  const [paymentOrder, setPaymentOrder] = useState(null);
  const [accountTab, setAccountTab] = useState('overview');
  const authOpener = useRef(null);
  const user = account.user;
  async function refresh() {
    const [c, a] = await Promise.all([api('catalog/'), api('me/')]);
    setCatalog(c); setAccount(a); setLoadError('');
    setDay(current => current || (c.classes[0] ? dayKey(c.classes[0].starts_at) : ''));
  }
  useEffect(() => {
    api('csrf/').then(refresh).catch(e => setLoadError(e.message));
    const result = new URLSearchParams(window.location.search).get('payment');
    if (result) {
      if (result === 'success') setPaymentOrder(new URLSearchParams(window.location.search).get('order'));
      setNotice({ type: 'info', text: result === 'success' ? 'Wróciłeś z płatności. Karnet pojawi się po potwierdzeniu przez Stripe. W panelu możesz odświeżyć status.' : 'Płatność została przerwana. Możesz ponownie wybrać karnet.' });
      window.history.replaceState({}, '', window.location.pathname + window.location.hash);
    }
  }, []);
  useEffect(() => {
    if (!paymentOrder || !user) return;
    let stopped = false;
    let timer;
    let attempts = 0;
    async function checkPayment() {
      try {
        const data = await api('me/');
        if (stopped) return;
        setAccount(data);
        const order = data.orders?.find(o => o.id === paymentOrder);
        if (order?.status === 'paid') {
          setPaymentOrder(null);
          setNotice({ type: 'success', text: 'Płatność testowa potwierdzona. Twój karnet jest gotowy!' });
          return;
        }
        if (order?.status === 'failed') {
          setPaymentOrder(null);
          setNotice({ type: 'error', text: 'Płatność nie została zakończona. Możesz ponownie wybrać karnet.' });
          return;
        }
      } catch {
        // Confirmation can arrive later; leave manual refresh available.
      }
      if (!stopped && ++attempts < 15) timer = setTimeout(checkPayment, 2000);
    }
    checkPayment();
    return () => { stopped = true; clearTimeout(timer); };
  }, [paymentOrder, user?.id]);
  useEffect(() => {
    if (!notice || notice.type === 'info') return;
    const timer = setTimeout(() => setNotice(null), 7000);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!auth) return;
    const before = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = before; authOpener.current?.focus(); };
  }, [auth]);
  function openAuth(action = null) {
    authOpener.current = document.activeElement;
    setPending(action); setAuth('login'); setMobile(false);
  }
  async function perform(key, action) {
    setBusy(key);
    try { await action(); } catch (e) { setNotice({ type: 'error', text: e.message }); }
    finally { setBusy(''); }
  }
  function buy(plan) {
    if (!user) return openAuth({ type: 'buy', plan });
    return perform(`plan-${plan.id}`, async () => {
      const data = await api('checkout/', { method: 'POST', body: { plan_id: plan.id } });
      window.location.assign(data.url);
    });
  }
  function book(c) {
    if (!user) return openAuth({ type: 'book', gymClass: c });
    return perform(`class-${c.id}`, async () => {
      await api(`classes/${c.id}/book/`, { method: 'POST' }); await refresh();
      setNotice({ type: 'success', text: `Miejsce na ${c.name} jest Twoje. Do zobaczenia!` });
    });
  }
  async function authenticated(data) {
    const action = pending;
    setAuth(null); setPending(null); setAccount({ user: data });
    await refresh();
    // A second click makes the intended purchase/booking explicit after sign-in.
    setNotice({ type: 'success', text: action ? 'Jesteś zalogowany. Wybierz ponownie karnet lub zajęcia, aby kontynuować.' : `Cześć, ${data.name}! Dobrze Cię widzieć.` });
  }
  const days = [...new Set(catalog?.classes.map(c => dayKey(c.starts_at)) || [])];
  const visibleClasses = catalog?.classes.filter(c => dayKey(c.starts_at) === day && (location === 'all' || String(c.location.id) === location) && (category === 'all' || c.category === category)) || [];
  const active = account.memberships?.find(m => new Date(m.starts_at) <= new Date() && new Date(m.ends_at) > new Date());

  return <>
    <div className="announcement">TWOJE PIERWSZE POWTÓRZENIE ZACZYNA SIĘ TUTAJ <span>↗</span></div>
    <header className="header"><a className="logo" href="#start" aria-label="FitZone — strona główna"><Dumbbell strokeWidth={2.8}/><span>fitzone<span className="logo-dot">.</span></span></a>
      <button className="mobile-toggle icon-button" onClick={() => setMobile(!mobile)} aria-expanded={mobile} aria-label="Menu">{mobile ? <X/> : <Menu/>}</button>
      <nav className={mobile ? 'nav open' : 'nav'} aria-label="Menu główne">
        <a href="#grafik" onClick={() => setMobile(false)}>Grafik zajęć</a><a href="#karnety" onClick={() => setMobile(false)}>Karnety</a><a href="#kluby" onClick={() => setMobile(false)}>Nasze kluby</a>
        {user ? <a className="account-button" href="#konto" onClick={() => setMobile(false)}><UserRound size={17}/>Moje konto</a> : <button className="account-button" onClick={() => openAuth()}><UserRound size={17}/> Zaloguj się</button>}
        <a className="button small lime" href="#karnety" onClick={() => setMobile(false)}>Dołącz do nas <ArrowUpRight size={17}/></a>
      </nav>
    </header>
    <main>
      <section id="start" className="hero section-width">
        <div className="hero-copy"><div className="eyebrow"><span className="pulse-dot"/> WIĘCEJ NIŻ SIŁOWNIA</div>
          <h1>TWÓJ RUCH.<br/>TWOJE <span>MIEJSCE.</span></h1>
          <p>Nie musisz być w formie, żeby zacząć.<br/>Znajdź swój rytm. My zadbamy o resztę.</p>
          <div className="hero-actions"><a className="button lime" href="#karnety">Znajdź swój karnet <ArrowUpRight size={20}/></a><a className="text-link" href="#grafik">Zobacz grafik <ArrowRight size={18}/></a></div>
          <div className="hero-proof"><div className="proof-icon"><Dumbbell size={18}/></div><span>Siła. Energia. Dobra ekipa.<br/><strong>Wszystko w Twoim tempie.</strong></span></div>
        </div>
        <div className="hero-art" aria-hidden="true"><div className="art-grid"/><div className="art-label">MAKE<br/>YOUR<br/><span>MOVE.</span></div><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="art-arrow"><MoveUpRight strokeWidth={1.1}/></div><div className="art-bottom"><span>52°13′ N / 21°00′ E</span><span>WARSZAWA, PL</span></div><div className="art-sticker">100%<small>TWOJEGO TEMPA</small></div></div>
      </section>
      <div className="features-strip"><div className="section-width"><span><Check/>Karnety bez automatycznego odnawiania</span><span><Check/>Zajęcia grupowe w cenie</span><span><Check/>Dwa kluby. Jeden karnet.</span></div></div>

      {loadError && <div className="section-width load-error" role="alert"><AlertCircle/><div><strong>Nie udało się pobrać oferty.</strong><p>{loadError}</p></div><button className="button outline" onClick={() => perform('refresh', refresh)}>Spróbuj ponownie</button></div>}

      <section id="grafik" className="section section-width">
        <div className="section-heading"><div><div className="eyebrow muted">01 / ZNAJDŹ SWOJĄ ENERGIĘ</div><h2>Twój plan na lepszy dzień<span>.</span></h2></div><p>Wybierz zajęcia i zarezerwuj miejsce.<br/>Resztę zostaw na sali.</p></div>
        {!catalog && !loadError ? <div className="loading"><LoaderCircle className="spin"/> Ładujemy grafik…</div> : <>
          <div className="schedule-tools"><div className="days" aria-label="Dzień zajęć">{days.slice(0, 7).map(d => <button key={d} onClick={() => setDay(d)} className={day === d ? 'day selected' : 'day'} aria-pressed={day === d}><span>{date(d + 'T12:00:00', { weekday: 'short', day: undefined, month: undefined })}</span><strong>{date(d + 'T12:00:00', { day: '2-digit', month: undefined })}</strong></button>)}</div>
            <div className="filters"><label><span>Klub</span><select value={location} onChange={e => setLocation(e.target.value)}><option value="all">Wszystkie kluby</option>{catalog?.locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label><label><span>Rodzaj zajęć</span><select value={category} onChange={e => setCategory(e.target.value)}><option value="all">Wszystkie zajęcia</option>{[...new Set(catalog?.classes.map(c => c.category))].map(c => <option key={c}>{c}</option>)}</select></label></div>
          </div>
          <div className="schedule-list">{visibleClasses.map((c, i) => <article className="class-row" key={c.id}><div className="class-time"><strong>{hour(c.starts_at)}</strong><span>{c.duration} min</span></div><div className={`class-mark mark-${i % 3}`}><Dumbbell size={22}/></div><div className="class-name"><span className="category">{c.category}</span><h3>{c.name}</h3><span className="mobile-location">{c.location.name}</span></div><div className="class-details"><span>{c.trainer}</span><small><MapPin size={13}/>{c.location.name}</small></div><span className={c.available ? 'spots' : 'spots full'}><i/>{c.available ? `${c.available} wolnych miejsc` : 'Brak miejsc'}</span><button className={c.booked ? 'button booked' : 'button outline'} disabled={!!busy || c.booked || !c.available} onClick={() => book(c)}>{busy === `class-${c.id}` ? <LoaderCircle className="spin" size={17}/> : c.booked ? <><Check size={16}/> Zapisano</> : <>Zapisz się <ArrowUpRight size={16}/></>}</button></article>)}{catalog && !visibleClasses.length && <div className="empty">Brak zajęć dla wybranych filtrów. Sprawdź inny dzień lub klub.</div>}</div>
          <p className="schedule-note"><CalendarDays size={15}/>{day ? date(day + 'T12:00:00', { year: 'numeric' }) : 'Grafik pojawi się wkrótce'} <span>·</span> Zapisy z aktywnym karnetem <span>·</span> Godziny lokalne: Warszawa</p>
        </>}
      </section>

      <section id="karnety" className="plans-section"><div className="section section-width"><div className="section-heading"><div><div className="eyebrow muted">02 / ZAINWESTUJ W SIEBIE</div><h2>Mały krok. Duża zmiana<span>.</span></h2></div><p>Proste zasady, pełen dostęp.<br/>Wybierz tempo dla siebie.</p></div><div className="plans">{catalog?.plans.map(p => <article className={p.featured ? 'plan featured' : 'plan'} key={p.id}>{p.featured && <div className="plan-ribbon">TWÓJ CODZIENNY DOŁADUNEK <span>↗</span></div>}<span className="plan-duration">{p.days === 1 ? 'WEJŚCIE JEDNORAZOWE' : `${p.days} DNI DLA SIEBIE`}</span><h3>{p.name}</h3><p>{p.description}</p><div className="price">{money(p.price)}<small>/ {p.days === 1 ? 'dzień' : `${p.days} dni`}</small></div><div className="plan-divider"/><ul>{['Dostęp do obu klubów', 'Strefa siłowa i cardio', 'Zajęcia grupowe w cenie', 'Rezerwacje online'].map(f => <li key={f}><Check size={16}/>{f}</li>)}</ul><button className={p.featured ? 'button dark' : 'button outline'} onClick={() => buy(p)} disabled={!!busy}>{busy === `plan-${p.id}` ? <LoaderCircle className="spin" size={18}/> : <>Wybieram ten karnet <ArrowUpRight size={18}/></>}</button></article>)}</div><p className="payment-note">Projekt demonstracyjny · płatności Stripe w trybie testowym · bez pobierania prawdziwych pieniędzy{catalog && !catalog.payments_enabled && <span>Integracja wymaga jeszcze podłączenia kluczy Stripe.</span>}</p></div></section>

      <section id="kluby" className="section section-width"><div className="section-heading"><div><div className="eyebrow muted">03 / BLIŻEJ, NIŻ MYŚLISZ</div><h2>Twoja energia ma swój adres<span>.</span></h2></div><p>Dwa miejsca. Ta sama dobra atmosfera.<br/>Trenuj tam, gdzie Ci wygodnie.</p></div><div className="locations">{catalog?.locations.map((l, i) => <article className="location" key={l.id}><div className={`location-visual visual-${i}`} aria-hidden="true"><div className="map-grid"/><span className="map-road road-one"/><span className="map-road road-two"/><div className="map-pin"><MapPin size={26}/></div><span className="map-coordinate">{i === 0 ? 'CENTRUM' : 'MOKOTÓW'}</span><span className="club-number">0{i + 1}</span></div><div className="location-body"><h3>{l.name}</h3><p><MapPin size={16}/>{l.address}</p><p><Clock3 size={16}/>{l.hours}</p><a href={l.maps_url} target="_blank" rel="noreferrer" className="text-link">Wyznacz trasę <ArrowUpRight size={17}/></a></div></article>)}</div><p className="demo-note">FitZone to fikcyjna sieć siłowni stworzona na potrzeby projektu. Adresy służą demonstracji.</p></section>

      {user && <section id="konto" className="section section-width account-section"><div className="section-heading"><div><div className="eyebrow muted">TWÓJ PANEL</div><h2>Cześć, {user.name}<span>.</span></h2></div><div className="account-actions"><button className="button outline" disabled={!!busy} onClick={() => perform('refresh', refresh)}>Odśwież status</button><button className="text-link" disabled={!!busy} onClick={() => perform('logout', async () => { await api('auth/logout/', { method: 'POST' }); await refresh(); })}><LogOut size={17}/>Wyloguj</button></div></div>
        <nav className="account-tabs" aria-label="Sekcje konta">
          <button type="button" aria-pressed={accountTab === 'overview'} aria-controls="account-overview" onClick={() => setAccountTab('overview')}>Karnet i rezerwacje</button>
          <button type="button" aria-pressed={accountTab === 'settings'} aria-controls="account-settings" onClick={() => setAccountTab('settings')}>Dane i bezpieczeństwo</button>
        </nav>
        <div id="account-settings" hidden={accountTab !== 'settings'}>
          {accountTab === 'settings' && <AccountSettings key={user.id} user={user} onPasswordChange={data => api('auth/password/', { method: 'POST', body: data })}/>}
        </div>
        <div id="account-overview" hidden={accountTab !== 'overview'}><div className="account-grid"><div className="membership-card"><span className="eyebrow">TWÓJ KARNET</span><h3>{active?.plan_name || 'Czas na pierwszy krok'}</h3>{active ? <><span className="member-status"><i/> AKTYWNY</span><p>Ważny do {date(active.ends_at, { year: 'numeric' })}, {hour(active.ends_at)}</p></> : <><p>Wybierz karnet i zyskaj dostęp do zajęć.</p><a className="button lime" href="#karnety">Zobacz karnety <ArrowUpRight size={17}/></a></>}{account.memberships?.filter(m => new Date(m.starts_at) > new Date()).map(m => <p key={m.id}>Kolejny: {m.plan_name}, od {date(m.starts_at)} do {date(m.ends_at)}</p>)}</div><div className="account-box"><h3>Twoje rezerwacje</h3>{account.bookings?.length ? account.bookings.map(b => <div className="booking-item" key={b.id}><div><strong>{b.gym_class.name}</strong><span>{date(b.gym_class.starts_at)} · {hour(b.gym_class.starts_at)}</span><small>{b.gym_class.location.name}</small></div><button className="text-link" disabled={!!busy} onClick={() => perform(`cancel-${b.id}`, async () => { await api(`bookings/${b.id}/`, { method: 'DELETE' }); await refresh(); setNotice({ type: 'success', text: 'Rezerwacja anulowana.' }); })}>Anuluj</button></div>) : <p className="muted">Nie masz jeszcze rezerwacji. Znajdź coś dla siebie w grafiku.</p>}</div></div><div className="order-history"><h3>Historia zakupów</h3>{account.orders?.length ? <div className="table-scroll"><table><thead><tr><th>Karnet</th><th>Data</th><th>Kwota</th><th>Status</th></tr></thead><tbody>{account.orders.map(o => <tr key={o.id}><td>{o.plan_name}</td><td>{date(o.created_at, { year: 'numeric' })}</td><td>{money(o.amount)}</td><td><span className={`order-status ${o.status}`}>{({ paid: 'Opłacone', pending: 'Oczekuje na płatność', failed: 'Nieudane' })[o.status]}</span></td></tr>)}</tbody></table></div> : <p className="muted">Twoje zakupy pojawią się tutaj.</p>}</div>{user.is_staff && <a className="text-link" href="/admin/">Otwórz panel administratora <ArrowUpRight size={16}/></a>}</div></section>}

      <section className="closing section-width"><span>NAJTRUDNIEJSZY JEST PIERWSZY KROK.</span><h2>Resztę zrobimy razem.</h2><a className="button lime" href="#karnety">Zaczynam dzisiaj <ArrowUpRight size={20}/></a></section>
    </main>
    <footer className="footer section-width"><a className="logo" href="#start"><Dumbbell/><span>fitzone.</span></a><p>Twój ruch. Twoje miejsce.</p><span>© {new Date().getFullYear()} FitZone · Projekt edukacyjny</span></footer>
    {notice && <div className={`toast ${notice.type}`} role={notice.type === 'error' ? 'alert' : 'status'}>{notice.type === 'error' ? <AlertCircle size={22}/> : <CheckCircle2 size={22}/>}<span>{notice.text}</span><button onClick={() => setNotice(null)} className="icon-button" aria-label="Zamknij komunikat"><X size={18}/></button></div>}
    {auth && <AuthModal mode={auth} setMode={setAuth} onClose={() => { setAuth(null); setPending(null); }} onSuccess={authenticated}/>}
  </>;
}

function AuthModal({ mode, setMode, onClose, onSuccess }) {
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const box = useRef(null);
  const register = mode === 'register';
  useEffect(() => { box.current?.querySelector('input')?.focus(); setError(''); }, [mode]);
  function handleKeys(e) {
    if (e.key === 'Escape' && !submitting) onClose();
    if (e.key === 'Tab') {
      const elements = [...box.current.querySelectorAll('button:not(:disabled), input, a[href]')];
      const first = elements[0], last = elements[elements.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }
  async function submit(e) {
    e.preventDefault(); setSubmitting(true); setError('');
    const data = Object.fromEntries(new FormData(e.currentTarget));
    try { await api('csrf/'); const user = await api(`auth/${register ? 'register' : 'login'}/`, { method: 'POST', body: data }); await onSuccess(user); }
    catch (e) { setError(e.message); } finally { setSubmitting(false); }
  }
  return <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget && !submitting) onClose(); }} onKeyDown={handleKeys}><div className="auth-modal" ref={box} role="dialog" aria-modal="true" aria-labelledby="auth-title"><button className="modal-close icon-button" disabled={submitting} onClick={onClose} aria-label="Zamknij"><X/></button><Dumbbell className="auth-brand" size={36}/><div className="eyebrow muted">TWOJA FORMA ZACZYNA SIĘ TUTAJ</div><h2 id="auth-title">{register ? 'Dołącz do ekipy.' : 'Dobrze Cię widzieć.'}</h2><p>{register ? 'Załóż konto, wybierz karnet i ruszaj na trening.' : 'Zaloguj się i zaplanuj kolejny trening.'}</p><form onSubmit={submit}>{register && <label>Imię<input name="name" autoComplete="given-name" maxLength={100} required placeholder="Jak masz na imię?"/></label>}<label>E-mail<input name="email" type="email" autoComplete="email" maxLength={150} required placeholder="twoj@email.pl"/></label><label>Hasło<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} minLength={register ? 10 : undefined} maxLength={128} required placeholder={register ? 'Co najmniej 10 znaków' : 'Twoje hasło'}/></label>{register && <small className="muted">Hasło nie może być popularne ani składać się wyłącznie z cyfr.</small>}{error && <div className="form-error" role="alert">{error}</div>}<button className="button lime" disabled={submitting}>{submitting ? <LoaderCircle className="spin" size={20}/> : <>{register ? 'Utwórz konto' : 'Zaloguj się'}<ArrowUpRight size={18}/></>}</button></form><div className="auth-switch">{register ? 'Masz już konto?' : 'Pierwszy raz w FitZone?'} <button disabled={submitting} onClick={() => setMode(register ? 'login' : 'register')}>{register ? 'Zaloguj się' : 'Załóż konto'}</button></div></div></div>;
}

createRoot(document.getElementById('root')).render(<App/>);

