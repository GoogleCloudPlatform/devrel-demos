export function mergeClassNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}