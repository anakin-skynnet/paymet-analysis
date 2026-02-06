import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/apx/navbar";
import { User } from "lucide-react";
import { BubbleBackground } from "@/components/backgrounds/bubble";

export const Route = createFileRoute("/")({
  component: () => <Index />,
});

function Index() {
  return (
    <div className="relative h-screen w-screen overflow-hidden flex flex-col">
      {/* Navbar */}
      <Navbar />

      {/* Main content - 2 columns */}
      <main className="flex-1 grid md:grid-cols-2">
        {/* Left column - Gradient only */}
        <BubbleBackground interactive />

        {/* Right column - Content */}
        <div className="relative flex flex-col items-center justify-center p-8 md:p-12 border-l">
          <div className="max-w-lg space-y-8 text-center">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold">
              Welcome to {__APP_NAME__}
            </h1>

            <Button size="lg" asChild>
              <Link to="/profile" className="flex items-center gap-2">
                <User className="h-5 w-5" />
                View <code>/profile</code>
              </Link>
            </Button>
          </div>
        </div>
      </main>

      {/* Background */}
      <div className="absolute inset-0 -z-10 h-full w-full bg-background" />
    </div>
  );
}
