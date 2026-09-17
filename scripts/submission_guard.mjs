export function normalizeMessage(value) {
  return String(value || '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('pt-BR');
}

export function hasExactMessage(messages, expected) {
  const wanted = normalizeMessage(expected);
  return wanted.length > 0 && messages.some((message) => normalizeMessage(message) === wanted);
}

export function hasPriorProjectIntroduction(messages, projectTitle) {
  const title = normalizeMessage(projectTitle);
  return messages.some((message) => {
    const text = normalizeMessage(message);
    const presentsTeam = text.includes('dois desenvolvedores full stack') ||
      text.includes('equipe de dois desenvolvedores full stack');
    return presentsTeam && (!title || text.includes(title));
  });
}
