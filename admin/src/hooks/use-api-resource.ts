import { useCallback, useEffect, useState } from "react"

interface ResourceState<T> {
  data: T | null
  error: string | null
  loading: boolean
}

export function useApiResource<T>(loader: () => Promise<T>) {
  const [reloadKey, setReloadKey] = useState(0)
  const [state, setState] = useState<ResourceState<T>>({
    data: null,
    error: null,
    loading: true,
  })

  useEffect(() => {
    let active = true
    setState((current) => ({ ...current, error: null, loading: true }))

    void loader()
      .then((data) => {
        if (active) setState({ data, error: null, loading: false })
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            data: null,
            error: error instanceof Error ? error.message : "Неизвестная ошибка.",
            loading: false,
          })
        }
      })

    return () => {
      active = false
    }
  }, [loader, reloadKey])

  const retry = useCallback(() => setReloadKey((key) => key + 1), [])
  return { ...state, retry }
}
