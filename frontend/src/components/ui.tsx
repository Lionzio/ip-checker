/**
 * Componentes básicos de todas as telas (S26-01): botão, link de texto e mensagem de erro, com a
 * mesma aparência, o mesmo foco visível e alvos de pelo menos 44 px nas telas de toque.
 */
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import { buttonClass, TEXT_LINK, type Variant } from "../ui";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className = "", type = "button", ...props }: ButtonProps) {
  return <button type={type} className={buttonClass(variant, className)} {...props} />;
}

export function TextLink({ className = "", ...props }: LinkProps) {
  return <Link className={`${TEXT_LINK} ${className}`.trim()} {...props} />;
}

/** Um erro que a pessoa precisa ler: anunciado ao leitor de tela, com contraste AA nos dois temas. */
export function ErrorText({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <p id={id} role="alert" className="text-sm text-red-700 dark:text-red-300">
      {children}
    </p>
  );
}
