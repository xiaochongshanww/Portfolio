export type ItemType = 'text' | 'image'

export interface Item {
  id: string
  type: ItemType
  text: string | null
  imageFile: string | null
  createdAt: number
  size: number
}

export interface ItemsResponse {
  items: Item[]
  serverTime: number
}
