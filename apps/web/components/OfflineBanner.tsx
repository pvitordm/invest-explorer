"use client";

type Props = {
  message: string;
  isOffline: boolean;
};

export function OfflineBanner({ message, isOffline }: Props) {
  if (!isOffline) return null;
  return (
    <div
      style={{
        background: "#fef3c7",
        border: "1px solid #f59e0b",
        borderRadius: 8,
        padding: "0.75rem",
        marginBottom: "1rem"
      }}
    >
      {message}
    </div>
  );
}
