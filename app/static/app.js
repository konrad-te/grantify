// Matching also works without JavaScript; this only improves form interactions.
const form = document.querySelector('#funding-form');
const button = document.querySelector('#submit-button');
function updateOtherFields() {
  document.querySelectorAll('[data-other-for]').forEach(container => {
    const key = container.dataset.otherFor;
    const selected = [...form.querySelectorAll(`[name="${key}"]`)].some(input =>
      input.tagName === 'SELECT' ? input.value === 'other' : input.checked && input.value === 'other');
    container.hidden = !selected;
    container.querySelector('input').required = selected;
  });
}
form.addEventListener('change', updateOtherFields);
form.addEventListener('submit', event => {
  if (!form.querySelector('[name="activities"]:checked')) {
    event.preventDefault();
    document.querySelector('#help-activities').textContent = 'Select at least one planned activity to continue.';
    form.querySelector('[name="activities"]').focus();
    return;
  }
  button.disabled = true;
  button.textContent = 'Checking programmes…';
  document.querySelector('#submit-status').textContent = 'Comparing your selections with the programme rules.';
});
window.addEventListener('pageshow', () => {
  button.disabled = false;
  button.textContent = 'Find funding';
  document.querySelector('#submit-status').textContent = '';
  updateOtherFields();
});
updateOtherFields();
// An edited example no longer has the authored expected outcome.
document.querySelector('#description').addEventListener('input', () => {
  const expected = document.querySelector('#example-expectation');
  if (expected) expected.hidden = true;
  document.querySelectorAll('.example-option[aria-current]').forEach(link => {
    link.removeAttribute('aria-current');
  });
});
const errors = document.querySelector('#form-errors');
if (errors) errors.focus();
const prepareButton = document.querySelector('#prepare-button');
document.querySelector('#description-form').addEventListener('submit', () => {
  prepareButton.disabled = true;
  prepareButton.textContent = 'Preparing your form…';
  document.querySelector('#prepare-status').textContent = 'Reading your description. This can take up to two minutes. You will review the answers next.';
});
window.addEventListener('pageshow', () => {
  prepareButton.disabled = false;
  prepareButton.textContent = 'Prepare my form';
  document.querySelector('#prepare-status').textContent = '';
});
const uploadToggle = document.querySelector('#upload-toggle');
const uploadPanel = document.querySelector('#upload-panel');
uploadToggle.addEventListener('click', () => {
  const isOpen = uploadToggle.getAttribute('aria-expanded') === 'true';
  uploadToggle.setAttribute('aria-expanded', String(!isOpen));
  uploadPanel.hidden = isOpen;
  if (!isOpen) document.querySelector('#project_document').focus();
});
form.addEventListener('input', event => {
  document.querySelectorAll('[data-evidence-for]').forEach(note => {
    if (note.dataset.evidenceFor === event.target.name) note.hidden = true;
  });
  const confirmation = document.querySelector('#review_confirmed');
  if (confirmation && event.target !== confirmation) confirmation.checked = false;
});
const review = document.querySelector('#profile-review');
if (review && !errors) review.focus();
const uploadButton = document.querySelector('#upload-button');
document.querySelector('#upload-form').addEventListener('submit', () => {
  uploadButton.disabled = true;
  uploadButton.textContent = 'Reading your document…';
  document.querySelector('#upload-status').textContent = 'Extracting the text and preparing your form. You will review the answers before matching.';
});
window.addEventListener('pageshow', () => {
  uploadButton.disabled = false;
  uploadButton.textContent = 'Prepare form from document';
  document.querySelector('#upload-status').textContent = '';
});
