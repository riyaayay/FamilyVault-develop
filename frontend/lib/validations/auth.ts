import { z } from "zod";

export const LoginSchema = z.object({
  email: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, { message: "Email is required." })
    .email({ message: "Please enter a valid corporate email address." }),
  password: z
    .string()
    .min(8, { message: "Password must be at least 8 characters long." }),
  rememberMe: z.boolean().optional(),
});

export type LoginInput = z.infer<typeof LoginSchema>;

export const SignUpSchema = z.object({
  fullName: z
    .string()
    .trim()
    .min(2, { message: "Please enter your full name." }),
  email: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, { message: "Email is required." })
    .email({ message: "Please enter a valid email address." }),
  password: z
    .string()
    .min(8, { message: "Password must be at least 8 characters long." }),
});

export type SignUpInput = z.infer<typeof SignUpSchema>;
