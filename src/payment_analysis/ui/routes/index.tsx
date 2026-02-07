import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/apx/navbar";
import Logo from "@/components/apx/logo";
import { motion } from "motion/react";
import { BarChart3, ShieldAlert, ArrowRight, CheckCircle2 } from "lucide-react";
import { BubbleBackground } from "@/components/backgrounds/bubble";

export const Route = createFileRoute("/")({
  component: () => <Index />,
});

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

const valueProps = [
  "Higher approval rates and conversion with smart routing and retry.",
  "Reduced risk and fraud via ML models and real-time decisioning.",
  "Full portfolio visibility with live dashboards and executive KPIs.",
  "Actionable insights so you know where to act next.",
];

function Index() {
  return (
    <div className="relative h-screen w-screen overflow-hidden flex flex-col bg-background">
      <Navbar leftContent={<Logo to="/" showText />} />

      <main className="flex-1 grid md:grid-cols-2 min-h-0">
        <BubbleBackground interactive />

        <div className="relative flex flex-col items-center justify-center p-8 md:p-12 lg:p-16 border-l border-border/50 bg-gradient-to-b from-background/98 via-background/95 to-background/98 backdrop-blur-md overflow-y-auto">
          <motion.div
            className="max-w-xl w-full space-y-8 text-center md:text-left"
            variants={container}
            initial="hidden"
            animate="show"
          >
            {/* Executive message — 1–2 lines, business value */}
            <motion.div variants={item} className="space-y-1">
              <p className="text-base md:text-lg font-medium text-primary">
                Higher approval rates. Lower risk. Better portfolio visibility.
              </p>
              <p className="text-sm text-muted-foreground">
                One platform for Getnet to maximize conversion and control.
              </p>
            </motion.div>

            <motion.h1
              variants={item}
              className="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight text-foreground leading-tight font-heading"
            >
              Risk & Portfolio Intelligence for Getnet
            </motion.h1>

            {/* Value proposition */}
            <motion.div variants={item} className="text-left">
              <p className="text-sm font-semibold text-foreground mb-3">
                What this solution does for Getnet
              </p>
              <ul className="space-y-2">
                {valueProps.map((text, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            </motion.div>

            {/* Teaser metric */}
            <motion.div
              variants={item}
              className="inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-4 py-2.5 text-sm font-medium text-primary"
            >
              <span>Portfolio approval rate</span>
              <span className="font-bold tabular-nums">— live in dashboard</span>
            </motion.div>

            {/* CTAs */}
            <motion.div
              variants={item}
              className="flex flex-col sm:flex-row gap-3 justify-center md:justify-start pt-2"
            >
              <Button
                size="lg"
                className="gap-2 min-w-[240px] h-12 text-base font-semibold shadow-lg hover:shadow-xl hover:shadow-primary/20 transition-all duration-200"
                asChild
              >
                <Link to="/dashboard">
                  <BarChart3 className="h-5 w-5" />
                  Explore portfolio performance
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 min-w-[200px] h-12 text-base font-medium"
                asChild
              >
                <Link to="/declines">
                  <ShieldAlert className="h-5 w-5" />
                  View risk insights
                </Link>
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
