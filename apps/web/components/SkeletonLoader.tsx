'use client';

/**
 * Skeleton Loader Components - Display during data loading
 * Simple CSS-based animations without external dependencies
 */

export function SkeletonText({ width = 'w-3/4', height = 'h-4' }: { width?: string; height?: string }) {
  return (
    <div className={`${width} ${height} bg-gray-300 dark:bg-gray-600 rounded animate-pulse`}></div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card animate-pulse">
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-4"></div>
      <div className="space-y-3">
        <SkeletonText width="w-full" height="h-4" />
        <SkeletonText width="w-5/6" height="h-4" />
        <SkeletonText width="w-4/5" height="h-4" />
      </div>
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="card animate-pulse">
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-4"></div>
      <div className="w-full h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
    </div>
  );
}

export function SkeletonStats() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="card animate-pulse">
          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-3/4 mb-2"></div>
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/2"></div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonAssetRow() {
  return (
    <div className="asset-row animate-pulse">
      <div className="space-y-2">
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2"></div>
        <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-2/3"></div>
      </div>
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="card animate-pulse">
      <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-4"></div>
      <div className="space-y-3">
        {[...Array(count)].map((_, i) => (
          <div key={i}>
            <SkeletonAssetRow />
            {i < count - 1 && <div className="h-px bg-gray-200 dark:bg-gray-700 my-3"></div>}
          </div>
        ))}
      </div>
    </div>
  );
}
