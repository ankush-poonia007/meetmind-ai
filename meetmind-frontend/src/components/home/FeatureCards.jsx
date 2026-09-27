import { UserCheck, MessageCircle, Bell, LayoutDashboard } from 'lucide-react';

/**
 * FeatureCards — Home Page Section 3 (Section 7)
 * Side-by-side feature cards showcasing core platform capabilities:
 * 1. Identity-Aware Extraction (UserCheck)
 * 2. Meeting Q&A (MessageCircle)
 * 3. Deadline Alerts (Bell)
 * 4. Multi-Meeting Dashboard (LayoutDashboard)
 *
 * Cards use .card container styling with scroll fade-up trigger attributes.
 */
function FeatureCards() {
  const features = [
    {
      id: 'identity-aware',
      icon: UserCheck,
      title: 'Knows who you are',
      description:
        'Tell MeetMind your name once. It finds you in the transcript and extracts only your tasks, mentions, and responsibilities.',
      delay: '0ms',
    },
    {
      id: 'meeting-qa',
      icon: MessageCircle,
      title: 'Ask anything',
      description:
        'Each meeting has its own AI chat. Ask what was decided, what someone said, or what your deadline is — answered from the transcript.',
      delay: '100ms',
    },
    {
      id: 'deadline-alerts',
      icon: Bell,
      title: "Alerts before it's late",
      description:
        'MeetMind monitors your deadlines daily and emails you before they arrive — with full context from the original meeting.',
      delay: '200ms',
    },
    {
      id: 'multi-meeting-dashboard',
      icon: LayoutDashboard,
      title: 'One view, all meetings',
      description:
        'Every task across every meeting in one filterable dashboard. Filter by priority, deadline, or status.',
      delay: '300ms',
    },
  ];

  return (
    <section className="features-section" id="features" aria-label="Feature Highlights">
      <div className="container">
        <div className="features-grid">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <article
                key={feature.id}
                className="card feature-card animate-fade-up"
                data-animate="fade-up"
                style={{ animationDelay: feature.delay }}
              >
                <div className="feature-icon-wrapper" aria-hidden="true">
                  <Icon className="feature-icon" size={28} />
                </div>
                <h3 className="text-h3 feature-title">{feature.title}</h3>
                <p className="text-body feature-description">{feature.description}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default FeatureCards;
