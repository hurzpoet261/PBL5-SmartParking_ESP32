import { useCallback, useState } from 'react';

export function useAsync<T>(asyncFn: () => Promise<T>) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const run = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      return await asyncFn();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [asyncFn]);

  return { loading, error, run, setError };
}
