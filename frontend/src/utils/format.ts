export const formatMoney = (value: string | number) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(Number(value || 0));

export const formatDateTime = (value?: string | null) => {
  if (!value) return '-';
  return new Date(value).toLocaleString('vi-VN');
};

export const labelize = (value: string) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, (char: string) => char.toUpperCase());
