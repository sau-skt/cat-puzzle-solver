export function passwordProblems(password: string): string[] {
  const problems: string[] = [];
  if (password.length < 8) problems.push("Use at least 8 characters.");
  if (!/[A-Z]/.test(password)) problems.push("Add an uppercase letter.");
  if (!/[a-z]/.test(password)) problems.push("Add a lowercase letter.");
  if (!/\d/.test(password)) problems.push("Add a digit.");
  if (!/[^A-Za-z0-9]/.test(password)) problems.push("Add a symbol.");
  return problems;
}
