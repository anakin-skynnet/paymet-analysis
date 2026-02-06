import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = false }: LogoProps) {
  const content = (
    <div className={`flex items-center gap-2 ${className}`}>
      <img
        src="/getnet_logo.png"
        alt="Getnet Payment Analysis"
        className="h-8 object-contain"
      />
      {showText && (
        <span className="font-semibold text-lg">{__APP_NAME__}</span>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="hover:opacity-80 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}

export default Logo;
