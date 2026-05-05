"use client";

import { type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { MOTION } from "@/lib/constants";

interface PageTransitionProps {
  children: ReactNode;
  id: string;
}

export function PageTransition({ children, id }: PageTransitionProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={id}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={MOTION.open}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
