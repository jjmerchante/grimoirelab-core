const formatDate = (date) => {
  if (typeof date !== 'object') {
    date = new Date(date)
  }
  const ISODate = date.toISOString().split(/[T.]/g)
  const formattedDate = `${ISODate[0]} ${ISODate[1]}`

  return formattedDate
}

const getDuration = (fromDate, toDate) => {
  if (fromDate && toDate) {
    const startDate = new Date(fromDate)
    const endDate = new Date(toDate)
    const diff = endDate - startDate
    const MS_MINUTE = 60 * 1000
    const MS_HOUR = MS_MINUTE * 60
    const MS_DAY = MS_HOUR * 24

    if (diff < MS_MINUTE) {
      return `${Math.floor(diff / 1000)}s`
    } else if (diff < MS_HOUR) {
      return `${Math.floor(diff / MS_MINUTE)}m ${Math.floor((diff % MS_MINUTE) / 1000)}s`
    } else if (diff < MS_DAY) {
      return `${Math.floor(diff / MS_HOUR)}h ${Math.floor((diff % MS_HOUR) / MS_MINUTE)}m`
    } else {
      return `${Math.floor(diff / MS_DAY)} days ${Math.floor((diff % MS_DAY) / MS_HOUR)}h`
    }
  } else {
    return null
  }
}

export { formatDate, getDuration }
