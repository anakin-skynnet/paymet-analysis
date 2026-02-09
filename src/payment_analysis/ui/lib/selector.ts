/** Selectors for TanStack Query hooks (e.g. select: (data) => data.data) for clean destructuring. */

export const selector = <T>() => ({
  query: {
    select: (data: { data: T }) => data.data,
  },
});

export default selector;
