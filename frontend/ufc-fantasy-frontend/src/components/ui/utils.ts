import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Helper function to combine CSS classes without breaking stuff for the animated list.
 * 
 * When I tried to merge default styles with custom styles, it would break the animated list.
 * 
 * Combines all the classes together.
 */