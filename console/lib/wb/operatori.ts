// Mapping operative BackOperation (hr.employee.id → nome), da brief wallboard.
// Statico di proposito: evita di richiedere ACL read su hr.employee al gruppo console_api.
export const BO_OPERATORI: Record<number, string> = {
  9: "Maria",
  6: "Teresa",
  3: "Anna",
  10: "Valentina",
};

export function nomeOperatore(employeeId: number | false | null | undefined): string {
  if (!employeeId) return "—";
  return BO_OPERATORI[employeeId] ?? `#${employeeId}`;
}

/** QC bloccanti instradati a Maria (employee id 9). */
export const MARIA_EMPLOYEE_ID = 9;
