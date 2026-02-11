import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = false }: LogoProps) {
  const content = (
    <div
      className={`flex flex-col items-center justify-center gap-2 py-2 px-2 min-h-[3rem] min-w-0 ${className}`}
      style={{ contain: "layout" }}
    >
      <span className="media-container h-9 max-h-9 w-full shrink-0">
        <img
          src="/getnet_logo.png"
          alt="Payment Analysis"
          className="max-h-9 h-auto w-auto max-w-full object-contain object-center"
        />
      </span>
      {showText && (
        <span className="font-semibold text-sm font-heading leading-tight shrink-0 text-center px-0.5">{__APP_NAME__}</span>
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
