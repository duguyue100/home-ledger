import { ref } from 'vue'

// global mutation counter — composables watch this to refetch ("live update")
export const dataVersion = ref(0)
export function bumpData(): void {
  dataVersion.value++
}
