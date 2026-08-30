export default function StatusBanner({ tone = 'info', children }) {
  const styles = {
    info: 'bg-sky-500/10 text-sky-700 dark:text-sky-300',
    error: 'bg-rose-500/10 text-rose-700 dark:text-rose-300',
    success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  }
  return <div className={`rounded-2xl px-4 py-3 text-sm ${styles[tone]}`}>{children}</div>
}
