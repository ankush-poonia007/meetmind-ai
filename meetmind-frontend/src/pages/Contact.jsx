import { Mail, Github, Linkedin, Phone, ArrowRight } from 'lucide-react';

/**
 * Contact — Page 4 (Section 10)
 *
 * Implements:
 * - Two-column responsive layout (Left: Contact Info, Right: Contact Form & Social Cards).
 * - Documented contact details: Email, GitHub, LinkedIn, and Phone.
 * - 5-field form visual structure: Full Name, Email Address, Category dropdown, Subject, Message.
 * - Three interactive social link cards below the form with hover elevation animation.
 *
 * Note: Form submission, mailto dispatch, and validation are reserved for Batch 7.2.
 */
function Contact() {
  return (
    <div className="contact-page page-enter">
      <div className="contact-container">
        {/* ── Left Column: Contact Information ─────────────────────────── */}
        <section className="contact-info-column" aria-labelledby="contact-info-heading">
          <p className="text-label contact-label-tag">Contact</p>
          <h1 className="text-h2 contact-title" id="contact-info-heading">
            Get in touch
          </h1>
          <p className="text-body-lg contact-intro">
            Have a question about MeetMind, want to collaborate, or just want to say hello?
          </p>

          <div className="contact-channels" aria-label="Contact channels">
            {/* Email Channel */}
            <a
              href="mailto:pooniaankush007@gmail.com"
              className="contact-channel-item"
              aria-label="Send email to pooniaankush007@gmail.com"
            >
              <div className="contact-channel-icon" aria-hidden="true">
                <Mail size={20} />
              </div>
              <div className="contact-channel-content">
                <span className="contact-channel-label">Email</span>
                <span className="contact-channel-value">pooniaankush007@gmail.com</span>
              </div>
            </a>

            {/* GitHub Channel */}
            <a
              href="https://github.com/ankush-poonia007"
              target="_blank"
              rel="noopener noreferrer"
              className="contact-channel-item"
              aria-label="GitHub profile github.com/ankush-poonia007 (opens in new tab)"
            >
              <div className="contact-channel-icon" aria-hidden="true">
                <Github size={20} />
              </div>
              <div className="contact-channel-content">
                <span className="contact-channel-label">GitHub</span>
                <span className="contact-channel-value">github.com/ankush-poonia007</span>
              </div>
            </a>

            {/* LinkedIn Channel */}
            <a
              href="https://linkedin.com/in/ankush"
              target="_blank"
              rel="noopener noreferrer"
              className="contact-channel-item"
              aria-label="LinkedIn profile linkedin.com/in/ankush (opens in new tab)"
            >
              <div className="contact-channel-icon" aria-hidden="true">
                <Linkedin size={20} />
              </div>
              <div className="contact-channel-content">
                <span className="contact-channel-label">LinkedIn</span>
                <span className="contact-channel-value">linkedin.com/in/ankush</span>
              </div>
            </a>

            {/* Phone Channel */}
            <div className="contact-channel-item contact-phone-item" aria-label="Phone number +91 XXXXXXXXXX">
              <div className="contact-channel-icon" aria-hidden="true">
                <Phone size={20} />
              </div>
              <div className="contact-channel-content">
                <span className="contact-channel-label">Phone</span>
                <span className="contact-channel-value">+91 XXXXXXXXXX</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── Right Column: Contact Form & Social Cards ────────────────── */}
        <section className="contact-form-column" aria-labelledby="contact-form-heading">
          {/* Contact Form Card */}
          <div className="card contact-form-card">
            <h2 className="text-h3 contact-form-title" id="contact-form-heading">
              Send a Message
            </h2>
            <p className="text-body contact-form-subtitle">
              Fill out the details below and we will get back to you shortly.
            </p>

            <form
              className="contact-form"
              onSubmit={(e) => e.preventDefault()}
              noValidate
            >
              {/* Field 1: Full Name */}
              <div className="contact-form-group">
                <label htmlFor="contact-name" className="contact-form-label">
                  Full Name
                </label>
                <input
                  id="contact-name"
                  type="text"
                  name="fullName"
                  className="contact-form-input"
                  placeholder="e.g. Alex Morgan"
                  autoComplete="name"
                />
              </div>

              {/* Field 2: Email Address */}
              <div className="contact-form-group">
                <label htmlFor="contact-email" className="contact-form-label">
                  Email Address
                </label>
                <input
                  id="contact-email"
                  type="email"
                  name="email"
                  className="contact-form-input"
                  placeholder="e.g. alex@example.com"
                  autoComplete="email"
                />
              </div>

              {/* Field 3: Category Dropdown */}
              <div className="contact-form-group">
                <label htmlFor="contact-category" className="contact-form-label">
                  Category
                </label>
                <div className="contact-select-wrapper">
                  <select
                    id="contact-category"
                    name="category"
                    className="contact-form-select"
                    defaultValue="General Query"
                  >
                    <option value="General Query">General Query</option>
                    <option value="Collaboration">Collaboration</option>
                    <option value="Bug Report">Bug Report</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              {/* Field 4: Subject */}
              <div className="contact-form-group">
                <label htmlFor="contact-subject" className="contact-form-label">
                  Subject
                </label>
                <input
                  id="contact-subject"
                  type="text"
                  name="subject"
                  className="contact-form-input"
                  placeholder="Brief summary of your inquiry"
                />
              </div>

              {/* Field 5: Message Textarea */}
              <div className="contact-form-group">
                <label htmlFor="contact-message" className="contact-form-label">
                  Message
                </label>
                <textarea
                  id="contact-message"
                  name="message"
                  className="contact-form-textarea"
                  rows={5}
                  placeholder="Write your message here..."
                />
              </div>

              {/* Field 6: Submit Button */}
              <div className="contact-form-actions">
                <button
                  type="submit"
                  className="btn-primary contact-submit-btn"
                  id="contact-submit-button"
                >
                  <span>Send Message</span>
                  <ArrowRight size={18} className="contact-btn-icon" aria-hidden="true" />
                </button>
              </div>
            </form>
          </div>

          {/* Social Cards Below Form */}
          <div className="contact-social-cards" aria-label="Social and Direct Links">
            {/* GitHub Card */}
            <a
              href="https://github.com/ankush-poonia007"
              target="_blank"
              rel="noopener noreferrer"
              className="card contact-social-card"
              aria-label="GitHub Repository ankush-poonia007 (opens in new tab)"
            >
              <div className="contact-social-icon" aria-hidden="true">
                <Github size={22} />
              </div>
              <div className="contact-social-info">
                <span className="contact-social-title">GitHub</span>
                <span className="contact-social-meta">@ankush-poonia007</span>
              </div>
            </a>

            {/* LinkedIn Card */}
            <a
              href="https://linkedin.com/in/ankush"
              target="_blank"
              rel="noopener noreferrer"
              className="card contact-social-card"
              aria-label="LinkedIn profile linkedin.com/in/ankush (opens in new tab)"
            >
              <div className="contact-social-icon" aria-hidden="true">
                <Linkedin size={22} />
              </div>
              <div className="contact-social-info">
                <span className="contact-social-title">LinkedIn</span>
                <span className="contact-social-meta">in/ankush</span>
              </div>
            </a>

            {/* Email Card */}
            <a
              href="mailto:pooniaankush007@gmail.com"
              className="card contact-social-card"
              aria-label="Direct Email to pooniaankush007@gmail.com"
            >
              <div className="contact-social-icon" aria-hidden="true">
                <Mail size={22} />
              </div>
              <div className="contact-social-info">
                <span className="contact-social-title">Email</span>
                <span className="contact-social-meta">pooniaankush007@gmail.com</span>
              </div>
            </a>
          </div>
        </section>
      </div>
    </div>
  );
}

export default Contact;
