"use client"

import { MouseEventHandler } from "react";
import "./big-color-border-button.css";

export default function BigColorBorderButton({ className = "", children, onClick = () => {}, type="button" }: {className?: string, children: React.ReactNode, onClick?: MouseEventHandler<HTMLButtonElement>, type?: "button" | "submit" | "reset" }) {
  return (
    <button type={type} onClick={onClick} className={`color-border draw ${className}`}>
      {children}
    </button>
  )
}
