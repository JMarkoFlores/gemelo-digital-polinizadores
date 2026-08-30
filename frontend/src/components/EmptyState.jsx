export default function EmptyState({ title, description }) {
  return (
    <div className="rounded-[1.5rem] border border-dashed border-slate-300 px-5 py-10 text-center dark:border-slate-700">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  )
}
