import { resolve, relative } from 'path';

const VAULT_DIR = process.env.SECOND_BRAIN_VAULT_DIR?.trim()
  || process.env.VAULT_DIR?.trim()
  || resolve('../second-brain');

export const VAULT = VAULT_DIR;

export function assertInsideVault(path: string): string {
  const target = resolve(path);
  const rel = relative(VAULT, target);

  if (rel.startsWith('..') || rel === '..' || rel.startsWith('/')) {
    throw new Error(`Path outside Second Brain vault rejected: ${path}`);
  }

  return target;
}
