const insertScript = (path) =>
  new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = path;
    s.onload = () => resolve(s);  // resolve with script, not event
    s.onerror = reject;
    document.body.appendChild(s);
  });

var loadDeps = async function(baseurl){
    let scripts = [
      insertScript('https://cdn.jsdelivr.net/npm/vue@2.6.12'),
      insertScript('https://cdn.jsdelivr.net/npm/vue-async-computed@3.9.0'),
      insertScript('https://cdn.jsdelivr.net/npm/axios@0.21.0'),
      insertScript('https://cdn.jsdelivr.net/npm/lodash@4.17.20')
    ]
    const s = document.createElement('link');
    s.rel = 'stylesheet';
    s.href = baseurl+'/static/external.css';
    document.head.appendChild(s);
    await Promise.all(scripts);
};

const pub_html = `
<div class="publication_filters"><form action="javascript:void(0);" autocomplete="off">
  <div class="input search">
    <label for="search">Text search: </label>
    <div>
      <input type="text" name="search" v-model.trim="filters.search" />
      <div class="search_hint">To search for an exact phrase, enclose term in quotation marks.</div>
    </div>
  </div>
  <div class="col">
    <div class="input vcenter"><label for="start_date">Start date: </label><input type="date" name="start_date" v-model="filters.start_date" /></div>
    <div class="input vcenter"><label for="end_date">End date: </label><input type="date" name="end_date" v-model="filters.end_date" /></div>
    <div class="input"><label for="type">Type: </label>
      <radio class="type_box" type="type" :name_vals="publication_types" v-model="filters.type"></radio>
    </div>
  </div><div class="col" v-if="!filters.hide_projects">
    <div class="input"><label for="projects">Project: </label><div class="projects_box">
      <div class="checkbox" v-for="p in  Object.keys(projects)">
        <input type="checkbox" name="projects" :id="'projects_'+p" :value="p" v-model="filters.projects" />
        <label :for="'projects_'+p">{{ projects[p] }}</label>
      </div>
    </div></div>
  </div>
</form></div>
<div class="publication_list">
  <h2>Publications</h2>
  <div>
    <div class="publication_count">Search returned {{ count }} results</div>
    <div class="publication_header">
      <div class="publication_pagination">
        <div v-if="page > 1 || count >= limit">
          <a v-for="p in page_links" @click="setPage(p)" :aria-label="'Page '+p" :class="{publication_current: p == page, publication_numeric: !isNaN(p)}">{{ p }}</a>
        </div>
      </div>
      <div class="publication_set_limit"><label for="set_limit">Publications per Page: <input type="text" id="set_limit" v-model.number="limit" /></div>
    </div>
    <hr>
    <div v-if="typing">{{ typing }}</div>
    <div v-else>
      <pub v-for="pub in pubs" v-bind="pub" :project_labels="projects" :filters="filters"></pub>
      <hr>
      <div v-if="page > 1 || count >= limit" class="publication_pagination">
        <a v-for="p in page_links" @click="setPage(p)" :aria-label="'Page '+p" :class="{publication_current: p == page, publication_numeric: !isNaN(p)}">{{ p }}</a>
      </div>
    </div>
  </div>
</div>
`;

let URLSerializer = function(p){
  let ret = [];
  for(const k in p){
    let v = p[k]
    if (v === null || typeof v === undefined)
      continue
    if (!Array.isArray(v)) {
      v = [v]
    }
    for(const vv of v){
      ret.push(encodeURIComponent(k)+'='+encodeURIComponent(vv))
    }
  }
  return ret.join('&')
};

async function Pubs(id, baseurl = 'https://publications.icecube.aq', filters = {}, show_dates = false) {
  await loadDeps(baseurl);

  var updatePubs = async function(filters) {
    console.log('getting pubs for filters:')
    console.log(filters)
    const response = await axios.get(baseurl+'/api/publications', {
      params: filters,
      paramsSerializer: URLSerializer
    });
    console.log('pubs resp:')
    console.log(response.data)
    return response.data['publications'];
  };

  var updatePubsCount = async function(filters) {
    const response = await axios.get(baseurl+'/api/publications/count', {
      params: filters,
      paramsSerializer: URLSerializer
    });
    return response.data['count'];
  };

  // get data from server in parallel
  let filter_defaults_fut = axios.get(baseurl+'/api/filter_defaults');
  let publication_types_fut = (async function(){
    const response = await axios.get(baseurl+'/api/types');
    console.log('publication_types:')
    console.log(response.data)
    return response.data;
  })();
  let projects_fut = (async function(){
    const response = await axios.get(baseurl+'/api/projects');
    console.log('projects:')
    console.log(response.data)
    return response.data;
  })();
  let pubs_count_fut = updatePubsCount(filters);
  let pubs_filters = Object.assign({}, filters);
  pubs_filters['page'] = 0
  pubs_filters['limit'] = 20
  let pubs_fut = updatePubs(pubs_filters);

  // merge default filters
  const response = await filter_defaults_fut;
  var filters_with_defaults = response.data;
  Object.assign(filters_with_defaults, filters);

  // get publications
  let publication_types = await publication_types_fut;
  let projects = await projects_fut;
  let pubs = await pubs_fut;
  let pubsCount = await pubs_count_fut;

  Vue.component('pub', {
    props: {
      title: String,
      authors: String,
      abstract: String,
      type: String,
      citation: String,
      date: String,
      downloads: Array,
      projects: Array,
      sites: String,
      project_labels: Object,
      filters: Object
    },
    computed: {
        day_month_year: function() {
            const d = new Date(this.date);
            return d.getUTCDate()+' '+d.toLocaleString('default', { month: 'long', timeZone: 'UTC' })+' '+d.getUTCFullYear();
        },
        show_date: function() {
            return show_dates
        }
    },
    methods: {
      getDomain: function(u){
        try {
          if (!u.startsWith('http://') && !u.startsWith('https://') && !u.startsWith('://')) {
            u = 'http://'+u
          }
          return (new URL(u)).hostname;
        } catch {
          return u
        }
      }
    },
    template: `
<article class="publication">
  <div><span class="title">{{ title }}</span></div>
  <div><span class="authors" v-for="author in authors"><span class="author">{{ author }}</span></span></div>
  <div><span class="type">({{ type }})</span>
  <span class="citation">{{ citation }}</span>
  <span v-if="show_date" class="date">{{ day_month_year }}</span></div>
  <div class="abstract_div" v-if="abstract">Abstract: <span class="abstract">{{ abstract }}</span></div>
  <div>
    <span class="downloads" v-if="downloads">Download:
      <span class="download" v-for="link in downloads"><a :href="link" target="_blank">{{ getDomain(link) }}</a></span>
    </span>
    <span class="projects" v-if="projects && !filters.hide_projects">Project:
      <span class="project" v-for="project in projects">{{ project_labels[project] }}</span>
    </span>
  </div>
</article>`
  });

  Vue.component('radio', {
    props: {
      type: String,
      name_vals: Object,
      value: Array
    },
    computed: {
      checked: function(){
        let ch = {}
        for(const v in this.name_vals){
          ch[v] = (this.value.length > 0 && this.value[0] == v)
        }
        console.log('checked');console.log(ch)
        return ch
      }
    },
    methods: {
      changed: function(v){
        if (this.value.length > 0 && this.value[0] == v) { // uncheck
          this.value = []
        } else { // check
          this.value = [v]
        }
        this.$emit('input', this.value)
      }
    },
    template: `<div>
<div class="checkbox radio" :class="'checkbox_'+type" v-for="(n,v) in name_vals">
  <input type="checkbox" name="type" :id="type+'_'+v" :value="v" :checked="checked[v]" @input="changed(v)" />
  <label :for="type+'_'+v">{{ n }}</label>
</div></div>`
  })

  // write html
  if (id[0] == '#') {
    document.getElementById(id.substr(1)).innerHTML = pub_html;
  } else {
    console.error('bad id: '+id);
  }

  // start Vue
  var app = new Vue({
    el: id,
    data: {
      filters: filters_with_defaults,
      page: 1,
      limit: 20,
      pubs: pubs,
      count: pubsCount,
      publication_types: publication_types,
      projects: projects,
      refresh: 0,
      typing: ''
    },
    computed: {
      page_links: function(){
        let ret = []
        let pages = Math.ceil(this.count/this.limit);
        let first = Math.max(1, this.page - 3);
        let last = Math.min(pages, this.page + 3);

        if (this.page > 1) {
          ret.push('prev')
        }
        if (first > 1) {
          ret.push('first')
        }
        for(i=first;i<=last;i++){
          ret.push(i)
        }
        if (last < pages) {
          ret.push('last')
        }
        if (this.page < pages) {
          ret.push('next')
        }
        return ret
      }
    },
    watch: {
      filters: {
        handler: function(newFilters, oldFilters) {
          console.log("debouncing")
          this.typing = '...'
          this.page = 1
          this.debouncedUpdate()
        },
        deep: true
      },
      limit: function(newLimit, oldLimit) {
        if (newLimit == oldLimit) {
          return
        } else if (isNaN(newLimit) || newLimit < 1) {
          this.limit = oldLimit;
        } else {
          this.typing = '...'
          this.page = 1
          this.debouncedUpdate()
        }
      },
    },
    created: function() {
      this.debouncedUpdate = _.debounce(this.update, 250)
    },
    methods: {
      setPage: function(p) {
        if (p == 'next') {
          this.page += 1
        } else if (p == 'prev') {
          this.page -= 1
        } else if (p == 'first') {
          this.page = 1
        } else if (p == 'last') {
          this.page = Math.ceil(this.count/this.limit);
        } else if (!isNaN(p)) {
          this.page = p;
        } else {
          console.log('bad page: '+p)
          return
        }
        this.typing = '...'
        this.update()
      },
      update: async function() {
        let params = JSON.parse(JSON.stringify( this.filters ));
        params['page'] = this.page-1
        params['limit'] = this.limit
        const count_fut = updatePubsCount(params)
        const pubs_fut = updatePubs(params);
        this.count = await count_fut;
        this.pubs = await pubs_fut;
        this.typing = '';
      }
    }
  });
}
