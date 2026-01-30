export const formatDate = (timestamp: number): string => {
  if (!timestamp) return ''
  
  // Convert Unix timestamp (seconds) to milliseconds
  const date = new Date(timestamp * 1000)
  
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }
  
  // Format to "24 марта 2011 г."
  // The ' г.' part is specific to the Russian locale formatting for this options set.
  return date.toLocaleDateString('ru-RU', options)
}
