import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = false }: LogoProps) {
  const content = (
    <div
      className={`flex flex-col items-center justify-center gap-1.5 py-3 px-2 min-w-0 ${className}`}
    >
      <img
        src="/logo.png"
        alt="Payment Analysis"
        className="h-16 w-auto max-w-full object-contain rounded-md"
      />
      {showText && (
        <span className="font-semibold text-sm font-heading leading-tight shrink-0 text-center px-0.5">
          Payment Analysis
        </span>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="hover:opacity-90 transition-opacity duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-md">
        {content}
      </Link>
    );
  }

  return content;
}

export default Logo;
