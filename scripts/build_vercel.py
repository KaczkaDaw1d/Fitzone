"""Build React before Vercel's automatic Django collectstatic step.

Only production builds change the database. Set DATABASE_URL and other secrets
in the Vercel dashboard, never in source. Preview databases must be isolated.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(*command, env=None):
    subprocess.run(command, cwd=ROOT, env=env, check=True)

def main():
    corepack = shutil.which('corepack')
    npx = shutil.which('npx')
    if corepack:
        pnpm = [corepack, 'pnpm@11.25.0']
    elif npx:
        pnpm = [npx, '--yes', 'pnpm@11.25.0']
    else:
        raise RuntimeError('Build wymaga Node.js 22 i corepack lub npx.')
    run(*pnpm, '--dir', 'frontend', 'install', '--frozen-lockfile')
    run(*pnpm, '--dir', 'frontend', 'build')
    if os.getenv('VERCEL_ENV') == 'production':
        env = os.environ.copy()
        # Prefer Neon's direct connection for migrations; runtime can use pooler.
        if env.get('DATABASE_URL_UNPOOLED'):
            env['DATABASE_URL'] = env['DATABASE_URL_UNPOOLED']
        if not env.get('DATABASE_URL'):
            raise RuntimeError('Dodaj DATABASE_URL z Neon do środowiska Production.')
        run(sys.executable, 'manage.py', 'migrate', '--noinput', env=env)
        if env.get('SEED_DEMO') == '1':
            run(sys.executable, 'manage.py', 'seed_demo', env=env)
        run(sys.executable, 'manage.py', 'bootstrap_admin', env=env)

if __name__ == '__main__':
    main()
