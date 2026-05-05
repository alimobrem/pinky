"use client";

import { type ReactNode } from "react";
import { motion } from "motion/react";
import { MOTION } from "@/lib/constants";

interface FadeInProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function FadeIn({ children, className, delay = 0 }: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...MOTION.open, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
