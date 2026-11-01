export async function resolve(specifier, context, nextResolve) {
  if (['xlsx', 'jspdf', 'docx', 'file-saver'].includes(specifier)) {
    return {
      shortCircuit: true,
      url: new URL('./mock_deps.mjs', import.meta.url).href,
    }
  }
  return nextResolve(specifier, context)
}
