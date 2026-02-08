import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = false }: LogoProps) {
  const content = (
    <div className={`flex flex-col items-center justify-center gap-2 pt-1 pb-0.5 ${className}`}>
      <img
        src="/getnet_logo.png"
        alt="Payment Analysis"
        className="h-8 w-auto object-contain shrink-0"
      />
      {showText && (
        <span className="font-semibold text-lg font-heading leading-tight shrink-0">{__APP_NAME__}</span>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="hover:opacity-80 transition-opacity duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-md">
        {content}
      </Link>
    );
  }

  return content;
}

export default Logo;
