import { ModeToggle } from "@/components/apx/mode-toggle";
import Logo from "@/components/apx/logo";
import { ReactNode } from "react";

interface NavbarProps {
  leftContent?: ReactNode;
  rightContent?: ReactNode;
}

export function Navbar({ leftContent, rightContent }: NavbarProps) {
  return (
    <header className="z-50 bg-background/90 backdrop-blur-md border-b border-border/80 transition-colors duration-200 overflow-visible">
      <div className="min-h-[4.25rem] h-auto py-2 flex items-center justify-between gap-4 px-4 md:px-6">
        <div className="flex items-center min-h-[2.75rem] overflow-visible shrink-0">
          {leftContent || <Logo />}
        </div>
        <div className="flex-1 min-w-0" aria-hidden />
        <div className="flex items-center gap-2 shrink-0">
          {rightContent || <ModeToggle />}
        </div>
      </div>
    </header>
  );
}

export default Navbar;
