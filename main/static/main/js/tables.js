// DataTables dengan teks Tetun (perlu ditinjau penutur asli). Semua tabel dengan class "js-table".
(function () {
  if (!window.jQuery || !jQuery.fn.DataTable) return;
  jQuery(function ($) {
    $('table.js-table').each(function () {
      $(this).DataTable({
        pageLength: 25,
        order: [],
        language: {
          search: 'Buka:', lengthMenu: 'Hatudu _MENU_', info: 'Hatudu _START_ to _END_ husi _TOTAL_',
          infoEmpty: 'Laiha dadus', infoFiltered: '(filtru husi _MAX_)', zeroRecords: 'La hetan dadus',
          emptyTable: 'Laiha dadus', paginate: { first: 'Dahuluk', last: 'Ikus', next: 'Tuir', previous: 'Molok' },
        },
      });
    });
  });
})();
