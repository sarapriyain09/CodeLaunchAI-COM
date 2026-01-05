import './landing-legacy.css'
import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Landing() {
  const location = useLocation()

  const publicHref = (path: string) => {
    const rawBase = (import.meta as any).env?.VITE_PUBLIC_SITE_URL as string | undefined;
    const base = (rawBase || "").replace(/\/+$/, "");
    return base ? `${base}${path}` : path;
  };

  const scrollToId = (id: string) => {
    const element = document.getElementById(id)
    if (element) element.scrollIntoView()
  }

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const target = params.get('scroll')
    if (!target) return
    // Allow layout to paint before scrolling.
    window.setTimeout(() => scrollToId(target), 0)
  }, [location.search])

  return (
    <div className="landing-legacy">
      <div className="page-shell">
        <header>
          <div className="brand">Codlearn</div>
          <nav>
            <button className="nav-link" type="button" onClick={() => scrollToId('features')}>
              Features
            </button>
            <button className="nav-link" type="button" onClick={() => scrollToId('how-it-works')}>
              How it Works
            </button>
            <button className="nav-link" type="button" onClick={() => scrollToId('examples')}>
              Examples
            </button>
            <button className="nav-link" type="button" onClick={() => scrollToId('pricing')}>
              Pricing
            </button>
            <button className="nav-link" type="button" onClick={() => scrollToId('support')}>
              Support
            </button>
            <Link className="nav-link" to="/builder">
              App
            </Link>
          </nav>
        </header>

        <section className="hero">
          <div className="hero-copy">
            <div className="badge-row">
              <span className="badge">Students</span>
              <span className="badge">Web Developers</span>
              <span className="badge">Bootcamps</span>
            </div>
            <h1>Build Real Web Apps with AI in Minutes</h1>
            <p>
              Ship full-stack SaaS products with deploy-ready code, subscriptions, and learning-friendly
              guidance. Spark an idea, describe it, and let AI generate everything from frontend layouts
              to Stripe-powered payment flows.
            </p>
            <div className="cta-row">
              <Link className="cta primary" to="/builder">
                Get Started Free
              </Link>
              <button className="cta secondary" type="button">Watch Demo</button>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-screen">
              <pre>{`$ describe "Subscription habit tracker"
> generating UI, API, database...
> attaching Stripe billing, roles, analytics
✅ preview ready · deploy in 1 click`}</pre>
            </div>
          </div>
        </section>

        <section id="features">
          <h2 className="section-title">Launch-Ready Feature Stack</h2>
          <p className="section-subtitle">
            Everything students and indie devs need to go from sketch to deployable SaaS.
          </p>
          <div className="feature-grid">
            <div className="card">
              <div className="icon-circle">⚙️</div>
              <h3>Full-Stack Generation</h3>
              <p>AI assembles frontend, backend, and database schemas with auth, roles, and clean APIs.</p>
            </div>
            <div className="card">
              <div className="icon-circle">💳</div>
              <h3>Stripe Workflows</h3>
              <p>Subscription tiers, trials, and secure checkouts built in so you can charge from day one.</p>
            </div>
            <div className="card">
              <div className="icon-circle">🧠</div>
              <h3>Explainable Code</h3>
              <p>Inline narratives help students understand architecture and confidently edit any file.</p>
            </div>
            <div className="card">
              <div className="icon-circle">⚡</div>
              <h3>AI Credit System</h3>
              <p>Predictable usage caps keep experimentation affordable while rewarding smart prompts.</p>
            </div>
          </div>
        </section>

        <section id="how-it-works">
          <h2 className="section-title">From idea to deploy in four steps</h2>
          <p className="section-subtitle">
            Each step includes guided explanations so classrooms and teams learn while shipping.
          </p>
          <div className="steps-grid">
            <div className="card">
              <span className="step-number">STEP 01</span>
              <h3>Describe Your App</h3>
              <p>Use natural language or upload project briefs. Pick target audience, goals, and monetization.</p>
            </div>
            <div className="card">
              <span className="step-number">STEP 02</span>
              <h3>AI Generates Code</h3>
              <p>Receive full-stack scaffolding with reusable components, REST/GraphQL endpoints, and seeded data.</p>
            </div>
            <div className="card">
              <span className="step-number">STEP 03</span>
              <h3>Preview & Edit</h3>
              <p>Live playground with diff view, code annotations, and pair-programming style suggestions.</p>
            </div>
            <div className="card">
              <span className="step-number">STEP 04</span>
              <h3>Deploy & Monetize</h3>
              <p>Push to managed hosting, connect Stripe, and invite collaborators or mentors in one click.</p>
            </div>
          </div>
        </section>

        <section id="testimonials">
          <h2 className="section-title">Builders shipping faster</h2>
          <p className="section-subtitle">
            Student labs, hackathons, and indie founders use Codlearn to accelerate launch cycles.
          </p>
          <div className="testimonials">
            <div className="card">
              <blockquote>
                “I built my first subscription analytics tool between lectures. The AI commentary doubled as a tutor.”
              </blockquote>
              <cite>Jane · CS Student</cite>
            </div>
            <div className="card">
              <blockquote>
                “Stripe billing, user roles, and deployment ready in 30 minutes. Shipping MVPs has never felt this calm.”
              </blockquote>
              <cite>Rahul · Indie Developer</cite>
            </div>
          </div>
        </section>

        <section id="examples">
          <h2 className="section-title">Examples you can generate</h2>
          <p className="section-subtitle">
            A few realistic apps students and indie builders ship with the blueprint-first workflow.
          </p>
          <div className="examples-grid">
            <div className="card">
              <h3>Subscription Habit Tracker</h3>
              <p>Landing, auth, dashboard, Stripe tiers, email reminders.</p>
            </div>
            <div className="card">
              <h3>Local Business Booking Site</h3>
              <p>Services page, booking form, availability, contact, clean SEO structure.</p>
            </div>
            <div className="card">
              <h3>Course Cohort Portal</h3>
              <p>Projects list, assignments, submissions, announcements, student-friendly UI.</p>
            </div>
          </div>
        </section>

        <section id="pricing">
          <h2 className="section-title">Pricing that scales with ambition</h2>
          <p className="section-subtitle">
            Simple tiers with AI credits so you can plan semesters, bootcamps, or solo launches.
          </p>
          <p className="section-subtitle" style={{ marginTop: -20 }}>
            Free trial: 10 AI credits for 14 days.
          </p>

          <div className="pricing-grid">
            <div className="card">
              <h3>Student</h3>
              <p className="price">$10<span>/mo</span></p>
              <p>50 AI credits/month. Learning + small projects.</p>
              <a className="cta secondary" href={publicHref("/subscribe.html?plan=student&interval=month")}>Subscribe</a>
            </div>
            <div className="card">
              <h3>Pro</h3>
              <p className="price">$25<span>/mo</span></p>
              <p>300 AI credits/month. Full website + iterations.</p>
              <a className="cta primary" href={publicHref("/subscribe.html?plan=pro&interval=month")}>Subscribe</a>
            </div>
            <div className="card">
              <h3>Enterprise</h3>
              <p className="price">Custom</p>
              <p>Teams / agencies. Custom credits and support.</p>
              <a className="cta secondary" href="#support">Contact sales</a>
            </div>
          </div>
        </section>

        <section id="support">
          <h2 className="section-title">Privacy, terms, and live support</h2>
          <p className="section-subtitle">Transparent policies plus human help when you need it.</p>
          <div className="policy-grid">
            <div className="card">
              <h3>Privacy First</h3>
              <p>Projects stay encrypted at rest. Classroom data never trains public models. Export or delete anytime.</p>
              <a href="#">Read Privacy Policy</a>
            </div>
            <div className="card">
              <h3>Fair Terms</h3>
              <p>Clear usage rights for student IP, compliant with FERPA/GDPR, and transparent AI credit billing.</p>
              <a href="#">View Terms of Service</a>
            </div>
            <div className="card">
              <h3>Support & Success</h3>
              <p>24/7 chat for outages, weekday office hours with mentors, and dedicated success channels for schools.</p>
              <a href="#">Contact Support</a>
            </div>
          </div>
        </section>

        <footer>
          <div>© 2025 Codlearn · Powered by ethical AI</div>
          <ul>
            <li><a href="#">About</a></li>
            <li><a href="#">Docs</a></li>
            <li><a href="#">Blog</a></li>
            <li><a href="#">Contact</a></li>
            <li><a href="#">Privacy</a></li>
            <li><a href="#">Terms</a></li>
            <li><a href="#">Support</a></li>
          </ul>
        </footer>
      </div>
    </div>
  );
}
