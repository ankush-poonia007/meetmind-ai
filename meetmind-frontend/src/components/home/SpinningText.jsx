/**
 * SpinningText — Hero Section Circular Rotating Badge (Section 6 & 7)
 * Renders a circular SVG with rotating text path around the central MeetMind logo mark.
 * Text: "Agentic AI • Task Extraction • RAG Pipeline • Meeting Intelligence • "
 * Diameter: 220px.
 */
function SpinningText() {
  return (
    <div className="spinning-text-wrapper" aria-hidden="true">
      <svg
        className="spinning-text-svg"
        width="220"
        height="220"
        viewBox="0 0 220 220"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <path
            id="spinningTextPath"
            d="M 110, 110 m -78, 0 a 78,78 0 1,1 156,0 a 78,78 0 1,1 -156,0"
          />
        </defs>

        {/* Rotating Circular Text Ring */}
        <g className="spinning-text-ring">
          <text
            fill="var(--color-text-secondary)"
            fontSize="10.5"
            fontFamily="var(--font-sans)"
            fontWeight="500"
            letterSpacing="0.12em"
          >
            <textPath href="#spinningTextPath" startOffset="0%">
              Agentic AI • Task Extraction • RAG Pipeline • Meeting Intelligence •{' '}
            </textPath>
          </text>
        </g>

        {/* Static Center Abstract Icon: MeetMind Logo Mark */}
        <g transform="translate(94, 94)">
          <rect width="32" height="32" rx="8" fill="var(--color-accent-primary)" />
          <path
            d="M6 8C6 6.895 6.895 6 8 6H16C17.105 6 18 6.895 18 8V16C18 17.105 17.105 18 16 18H10L6 22V8Z"
            fill="white"
            opacity="0.95"
          />
          <path
            d="M14 12C14 10.895 14.895 10 16 10H24C25.105 10 26 10.895 26 12V20C26 21.105 25.105 22 24 22H22L18 26V12Z"
            fill="white"
            opacity="0.7"
          />
        </g>
      </svg>
    </div>
  );
}

export default SpinningText;
