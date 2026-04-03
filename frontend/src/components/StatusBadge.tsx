export default function StatusBadge({ value }: { value: string }) {
  return <span className={`badge badge-${value.replace(/_/g, '-')}`}>{value}</span>;
}
