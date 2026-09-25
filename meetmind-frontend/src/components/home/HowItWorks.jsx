/**
 * HowItWorks — Home Page Section 4 (Section 7)
 * Alternating step layout: step number large on one side, content on the other.
 * Step 1: Upload your transcript (PDF, TXT, or paste)
 * Step 2: MeetMind identifies you and extracts your tasks
 * Step 3: Confirm tasks, then chat, track, and get alerted
 */
function HowItWorks() {
  const steps = [
    {
      number: '01',
      title: 'Upload your transcript',
      description: 'Upload your transcript (PDF, TXT, or paste)',
    },
    {
      number: '02',
      title: 'Identify & Extract',
      description: 'MeetMind identifies you and extracts your tasks',
    },
    {
      number: '03',
      title: 'Confirm & Act',
      description: 'Confirm tasks, then chat, track, and get alerted',
    },
  ];

  return (
    <section className="how-it-works-section" id="how-it-works" aria-labelledby="how-it-works-heading">
      <div className="container">
        <div className="how-it-works-header">
          <p className="text-label">Process</p>
          <h2 className="text-h2" id="how-it-works-heading">
            How It Works
          </h2>
        </div>

        <div className="how-it-works-list">
          {steps.map((step, index) => (
            <div
              key={step.number}
              className={`how-it-works-step ${index % 2 === 1 ? 'step-alternate' : ''}`}
            >
              <div className="step-number" aria-hidden="true">
                {step.number}
              </div>
              <div className="step-content">
                <h3 className="text-h3 step-title">{step.title}</h3>
                <p className="text-body-lg step-description">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default HowItWorks;
