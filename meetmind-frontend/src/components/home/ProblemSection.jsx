/**
 * ProblemSection — Home Page Section 2 (Section 7)
 * Problem Statement section detailing the meeting transcript pain point.
 * 
 * Features:
 * - Pale blue surface background (#E3ECF7)
 * - Accent category label ("The problem")
 * - Serif headline with Wispr-style italic emphasis ("Meetings happen. Details get lost.")
 * - High-clarity dual paragraph explanation
 */
function ProblemSection() {
  return (
    <section
      className="problem-section"
      id="problem"
      aria-labelledby="problem-heading"
    >
      <div className="container">
        <div className="problem-content">
          <p className="text-label problem-label">The problem</p>
          <h2 className="text-h2 problem-heading" id="problem-heading">
            Meetings happen. <br />
            <em className="text-italic">Details get lost.</em>
          </h2>
          <div className="problem-body">
            <p className="text-body-lg">
              Every meeting produces tasks, decisions, and deadlines buried in
              long transcripts. Finding yours takes time you don't have.
            </p>
            <p className="text-body-lg">
              MeetMind reads the transcript, finds you in it, and gives you
              only what matters.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default ProblemSection;
