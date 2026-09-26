/**
 * Badge — Reusable UI Pill / Chip Component (Section 11)
 * Supports documented variants: high, medium, low, pending, complete, expired, and neutral.
 *
 * @param {object} props
 * @param {'high' | 'medium' | 'low' | 'pending' | 'complete' | 'expired' | 'neutral'} [props.variant='pending']
 * @param {React.ReactNode} props.children
 * @param {string} [props.className='']
 */
function Badge({ variant = 'pending', children, className = '', ...props }) {
  const variantClass = variant ? `badge-${variant}` : '';
  return (
    <span className={`badge ${variantClass} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
}

export default Badge;
